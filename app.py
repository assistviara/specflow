from flask import Flask, Blueprint, render_template, request, redirect, url_for, flash
from pathlib import Path
import json
import os
import secrets
import click

from human_control.web_runtime import Runtime
from human_control.sqlite_repository import HumanControlRepository
from human_control.project_ui import pages as project_pages

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


@legacy.route("/")
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


def create_app(db_path=None):
    application = Flask(__name__)
    application.secret_key = secrets.token_bytes(32)
    application.config.update(SESSION_COOKIE_HTTPONLY=True, SESSION_COOKIE_SAMESITE='Strict')
    runtime = Runtime(db_path)
    application.extensions['human_control'] = runtime
    application.register_blueprint(legacy)
    application.register_blueprint(project_pages)

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


app = create_app(os.environ.get('SPECFLOW_HUMAN_CONTROL_DB'))

if __name__ == "__main__":
    app.run(debug=False, threaded=False)
