"""One explicitly configured Workflow input set; no discovery or formal engine."""
from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
from uuid import uuid4

from flask import current_app, render_template, request, session

from core.approval_record_service import build_approval_record_from_artifact
from core.approval_validation import validate_approval_result
from human_control.projects import ProjectService
from human_control.web_runtime import BoundaryError
from human_control.workflows import explicit_path


def new_decision_identity():
    return str(uuid4()), datetime.now(timezone.utc).isoformat()


def lines(form, key):
    """Human selects the empty set explicitly; formatting is not a decision."""
    value = form.get(key, '')
    empty = form.get(key + '_none') == 'yes'
    if empty and value.strip():
        raise ValueError('空集合の選択と入力が矛盾しています: ' + key)
    if empty:
        return ()
    result = tuple(line.strip() for line in value.splitlines() if line.strip())
    if not result:
        raise ValueError('内容または「対象なし」を明示してください: ' + key)
    return result


@dataclass(frozen=True)
class PreparationSettings:
    root: Path
    repository: Path
    files: dict

    @classmethod
    def from_environment(cls, env, repository):
        root = explicit_path(env.get('SPECFLOW_WORKFLOW_ROOT', ''))
        if not root.is_dir():
            raise ValueError('SPECFLOW_WORKFLOW_ROOTには既存directoryが必要です。')
        roles = ('specification', 'constitution', 'principles', 'decisions',
                 'plan_template', 'plan_prompt_template', 'prompt_template')
        files = {role: explicit_path(env.get('SPECFLOW_INPUT_' + role.upper(), '')) for role in roles}
        revision = env.get('SPECFLOW_INPUT_REVISION_TEMPLATE', '')
        if revision:
            files['revision_template'] = explicit_path(revision)
        settings = cls(root, repository, files)
        settings.facts()
        return settings

    def facts(self):
        facts = {}
        if (not self.root.is_dir() or not self.repository.is_dir()
                or self.root.resolve() != self.root or self.repository.resolve() != self.repository):
            raise ValueError('設定済み保存先またはRepositoryがありません。')
        for role, path in self.files.items():
            if path.resolve() != path or not path.is_file():
                raise ValueError('正式入力が不足・変更されています: ' + role)
            if path.is_relative_to(self.root):
                raise ValueError('正式入力とWorkflow保存領域を分離してください。')
            facts[role] = (str(path), hashlib.sha256(path.read_bytes()).hexdigest())
        return facts


class WorkflowPreparation:
    def __init__(self, settings):
        self.settings = settings
        # Draft selections only. No Application Output or execution checkpoint.
        self.selections = {}

    def stamp(self, service, p):
        items = ProjectService(service.repository).constitution(p)
        return hashlib.sha256(repr((self.settings.facts(), items, str(self.settings.root),
                                    str(self.settings.repository))).encode()).hexdigest()

    def key(self, p):
        return session.get('_hc_session'), p

    def selected(self, service, p):
        value = self.selections.get(self.key(p))
        if value is None or value['stamp'] != self.stamp(service, p):
            raise BoundaryError('選択が失効したか正式入力・基本方針が変わりました。再確認してください。')
        return value

    def page(self, runtime, service, p):
        stamp = self.stamp(service, p)
        if request.method == 'GET':
            token = runtime.forms.issue('preparation:select', p, revision=stamp)
            return render_template('workflow_prepare.html', p=p, token=token, stage='select',
                                   specification=self.settings.files['specification'].name,
                                   repository=self.settings.repository)
        runtime.forms.consume(request.form.get('token'), 'preparation:select', p, revision=stamp)
        if request.form.get('specification_choice') != 'configured':
            raise ValueError('使用するSpecificationを明示選択してください。')
        if not ProjectService(service.repository).workflow_start_gate(p).allowed:
            raise ValueError('基本方針3項目の明示確認が必要です。')
        fields = {}
        for key in ('name', 'project_description', 'project_version'):
            fields[key] = request.form.get(key, '').strip()
            if not fields[key]:
                raise ValueError('意味の入力が必要です: ' + key)
        spec = self.settings.files['specification']
        content = spec.read_text(encoding='utf-8')
        if stamp != self.stamp(service, p):
            raise BoundaryError('表示中に正式入力が変更されました。')
        spec_hash = self.settings.facts()['specification'][1]
        workflow_id = uuid4()
        identity = str(uuid4())
        slot = self.settings.root / str(workflow_id)
        if slot.exists():
            raise BoundaryError('このProject・Specificationの準備記録が既にあります。再実行せず正式記録を確認してください。')
        value = dict(fields, stamp=stamp, identity=identity, workflow_id=workflow_id, slot=slot, approved=False,
                     specification_hash=spec_hash, project_name=service.repository.get_project(p).name)
        self.selections[self.key(p)] = value
        token = runtime.forms.issue('preparation:approve', p, revision=stamp)
        return render_template('workflow_prepare.html', p=p, token=token, stage='approve',
                               content=content, selection=value, repository=self.settings.repository)

    def approve(self, runtime, service, p, approvals):
        value = self.selected(service, p)
        runtime.forms.consume(request.form.get('token'), 'preparation:approve', p, revision=value['stamp'])
        if request.form.get('human_confirmed') != 'yes':
            raise ValueError('Specificationの承認を明示してください。')
        spec = self.settings.files['specification']
        # Exclusive reservation is an approval-attempt guard, not a resumable checkpoint.
        value['slot'].mkdir(exist_ok=False)
        record = build_approval_record_from_artifact(value['identity'], 'specification', str(spec),
            'approved', datetime.now(timezone.utc).isoformat(), 'Explicit Human Specification approval')
        if record['artifact_hash'] != value['specification_hash']:
            raise BoundaryError('承認対象が変更されました。')
        try:
            approvals.get(value['identity'])
        except FileNotFoundError:
            pass
        else:
            raise BoundaryError('Approval IDが衝突しました。上書きしません。')
        approvals.save(record)
        if approvals.get(value['identity']) != record or not validate_approval_result(
                record, str(spec), 'specification').is_valid:
            raise BoundaryError('正式Approvalの保存・検証に失敗しました。')
        value['record'] = record
        value['approved'] = True
        token = runtime.forms.issue('preparation:start', p, revision=value['stamp'])
        return render_template('workflow_prepare.html', p=p, token=token, stage='start',
                               selection=value, repository=self.settings.repository)

    def begin(self, runtime, service, p, approvals):
        value = self.selected(service, p)
        runtime.forms.consume(request.form.get('token'), 'preparation:start', p, revision=value['stamp'])
        if request.form.get('human_confirmed') != 'yes' or not value['approved']:
            raise ValueError('承認済みSpecificationからの開始を明示してください。')
        if not ProjectService(service.repository).workflow_start_gate(p).allowed:
            raise BoundaryError('基本方針Gateが閉じています。')
        record = approvals.get(value['identity'])
        if record != value['record'] or not validate_approval_result(record,
                str(self.settings.files['specification']), 'specification').is_valid:
            raise BoundaryError('Specification Approvalが変更・失効しています。')
        slot = value['slot']
        if slot.resolve() != slot or not slot.is_dir():
            raise BoundaryError('予約済み保存領域が変更されています。')
        # Consumed permanently even if subsequent registration/persistence fails.
        with (slot / 'start-attempt').open('x', encoding='utf-8') as stream:
            stream.write(str(value['workflow_id']))
        paths = dict(self.settings.files, state=slot / 'state.json', history=slot / 'history',
                     plan=slot / 'plan.md')
        with paths['state'].open('x', encoding='utf-8') as stream:
            json.dump({'status': 'specification_ready'}, stream)
        paths['history'].mkdir()
        values = {key: value[key] for key in ('name', 'project_name', 'project_description', 'project_version')}
        values.update(workflow_id=value['workflow_id'], approval_id=value['identity'], target_path=str(self.settings.repository))
        return values, paths

    def binding(self, work, paths):
        slot = paths['state'].parent
        expected = self.settings.root / str(work.workflow_id)
        legacy = self.settings.root / work.approval_id
        # Existing slots remain readable in place; never migrate formal artifacts.
        if slot == legacy:
            expected = legacy
        if slot != expected or slot.resolve() != slot or not (slot / 'start-attempt').is_file():
            raise BoundaryError('このWorkflowの限定準備記録を確認できません。')
        expected_identity = work.approval_id if slot == legacy else str(work.workflow_id)
        if (slot / 'start-attempt').read_text(encoding='utf-8') != expected_identity:
            raise BoundaryError('Workflow preparation identity mismatch.')
        self.settings.facts()
        for role, path in self.settings.files.items():
            if role not in paths or paths[role] != path:
                raise BoundaryError('正式入力の関連付けが起動設定と一致しません。')
        return slot

    def delegated_form(self, work, paths, form):
        slot = self.binding(work, paths)
        result = dict(form)
        result.update(repository=str(self.settings.repository), implementation_target=str(self.settings.repository),
            implementation_branch='impl/' + str(work.workflow_id), prompt_template=str(paths['prompt_template']),
            codex_prompt=str(slot / 'prompt.md'), review_dir=str(slot / 'reviews'), final_dir=str(slot / 'final'))
        for role in ('target_paths', 'allowed_changes', 'forbidden_changes'):
            result[role] = json.dumps(lines(form, role))
        for role in ('source_paths', 'test_paths'):
            selected = []
            for name in lines(form, role):
                relative = Path(name)
                if relative.is_absolute() or '..' in relative.parts:
                    raise ValueError('対象ファイルはRepository内の相対名で選択してください。')
                path = (self.settings.repository / relative).resolve()
                if not path.is_relative_to(self.settings.repository):
                    raise ValueError('対象ファイルがRepository外です。')
                selected.append(str(path))
            result[role] = json.dumps(selected)
        return result


def configured():
    if 'human_preparation' not in current_app.extensions:
        return None
    preparation = current_app.extensions['human_preparation']
    if preparation is None:
        raise ValueError('正式入力の関連付けまたはWorkflow保存rootが未設定・不正です。STOP。')
    return preparation
