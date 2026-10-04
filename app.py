from flask import Flask, Blueprint, render_template, request, redirect, url_for, flash
from pathlib import Path
import json
import os
import secrets
import click

from human_control.web_runtime import Runtime
from human_control.sqlite_repository import HumanControlRepository
from human_control.project_ui import pages as project_pages
from human_control.focus_ui import pages as focus_pages
from human_control.workflow_ui import pages as workflow_pages, continuity
from human_control.reminder_ui import pages as reminder_pages
from human_control.execution_ui import pages as execution_pages, ExecutionRuntime
from human_control.decision_ui import pages as decision_pages

legacy = Blueprint('legacy', __name__)

BASE_DIR = Path(__file__).resolve().parent
PROJECTS_DIR = BASE_DIR / "projects"


def get_project_dir(project_name: str) -> Path:
    return PROJECTS_DIR / project_name


def load_text(path: Path) -> str:
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8")


def save_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


@legacy.route("/legacy")
def index():
    projects = []
    if PROJECTS_DIR.exists():
        for project_dir in sorted(PROJECTS_DIR.iterdir()):
            if not project_dir.is_dir():
                continue

            state_path = project_dir / "state.json"
            state = {}
            if state_path.exists():
                state = json.loads(state_path.read_text(encoding="utf-8"))

            projects.append({
                "name": project_dir.name,
                "status": state.get("status", "未設定"),
            })

    return render_template("index.html", projects=projects)


@legacy.route("/projects/<project_name>", methods=["GET", "POST"])
def project_detail(project_name: str):
    project_dir = get_project_dir(project_name)
    spec_path = project_dir / "docs" / "specification.md"
    plan_path = project_dir / "docs" / "implementation_plan.md"
    log_path = project_dir / "logs" / "latest.txt"

    if request.method == "POST":
        specification = request.form.get("specification", "")
        save_text(spec_path, specification)
        flash("仕様書を保存しました。")
        return redirect(url_for("legacy.project_detail", project_name=project_name))

    return render_template(
        "project_detail.html",
        project_name=project_name,
        specification=load_text(spec_path),
        implementation_plan=load_text(plan_path),
        latest_log=load_text(log_path),
    )


def create_app(db_path=None, *, approvals_dir=None, evidence_dir=None, execution_factory=None):
    application = Flask(__name__)
    application.secret_key = secrets.token_bytes(32)
    application.config.update(SESSION_COOKIE_HTTPONLY=True, SESSION_COOKIE_SAMESITE='Strict')
    runtime = Runtime(db_path)
    application.extensions['human_control'] = runtime
    application.extensions['human_execution'] = ExecutionRuntime(execution_factory)
    application.extensions['human_decisions'] = {}
    if runtime.failure is None:
        application.extensions['human_continuity'] = continuity(
            runtime.require_repository(), approvals_dir, evidence_dir)
    application.register_blueprint(legacy)
    application.register_blueprint(project_pages)
    application.register_blueprint(focus_pages)
    application.register_blueprint(workflow_pages)
    application.register_blueprint(reminder_pages)
    application.register_blueprint(execution_pages)
    application.register_blueprint(decision_pages)

    @application.before_request
    def database_boundary():
        if runtime.failure is not None and request.endpoint != 'static':
            return render_template('human_control_unavailable.html', failure=runtime.failure), 503

    @application.cli.command('init-human-control-db')
    @click.option('--path', required=True, type=click.Path(path_type=Path))
    def initialize_database(path):
        """Explicit create-only initialization, independent from normal startup."""
        try:
            HumanControlRepository.initialize(path)
        except Exception:
            raise click.ClickException('DB初期化に失敗しました。対象を削除・置換せず保持しました。') from None
        click.echo(f'Human Control DBを新規作成しました: {path.resolve()}')

    return application


def create_environment_app(env=None):
    """Standard startup; settings are explicit and no execution occurs here."""
    from human_control.runtime_composition import ExecutionSettings, ProductionFactory
    from human_control.project_ui import problem

    env = os.environ if env is None else env
    settings, failure = None, ''
    try:
        settings = ExecutionSettings.from_environment(env)
    except ValueError as exc:
        failure = str(exc)
    except OSError:
        failure = '実行設定のdirectoryを確認できません。'
    application = create_app(env.get('SPECFLOW_HUMAN_CONTROL_DB'),
        approvals_dir=settings.approvals if settings else env.get('SPECFLOW_APPROVALS_DIR'),
        evidence_dir=settings.evidence if settings else env.get('SPECFLOW_EVIDENCE_DIR'),
        execution_factory=ProductionFactory(settings) if settings else None)

    @application.before_request
    def execution_settings_boundary():
        execution_post = request.blueprint == 'human_execution' and request.method == 'POST'
        final_post = request.blueprint == 'human_decisions' and request.method == 'POST'
        start_page = request.endpoint == 'human_execution.new'
        if not (execution_post or final_post or start_page):
            return None
        if failure:
            return problem('STOP: ' + failure, 503)
        try:
            if (request.endpoint == 'human_execution.act'
                    and request.view_args.get('action') == 'decide'
                    and request.form.get('human_decision') == 'approved'):
                settings.check_repository(request.form.get('repository', ''))
            if final_post:
                runtime = application.extensions['human_control']
                _, w = runtime.target(request.view_args['project_id'], request.view_args['workflow_id'])
                refs = runtime.require_repository().artifact_references(w)
                settings.check_repository(refs.get('repository', ''))
        except (ValueError, OSError):
            return problem('STOP: 対象RepositoryまたはProject / Workflowの対応を確認できません。', 409)
        except Exception:
            return problem('STOP: 実行対象の管理情報を確認できません。', 503)

    return application


app = create_environment_app()

if __name__ == "__main__":
    app.run(debug=False, threaded=False)
