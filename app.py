from flask import Flask, render_template, request, redirect, url_for, flash
from pathlib import Path
import json

app = Flask(__name__)
app.secret_key = "change-this-secret-key"

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


@app.route("/")
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


@app.route("/projects/<project_name>", methods=["GET", "POST"])
def project_detail(project_name: str):
    project_dir = get_project_dir(project_name)
    spec_path = project_dir / "docs" / "specification.md"
    plan_path = project_dir / "docs" / "implementation_plan.md"
    log_path = project_dir / "logs" / "latest.txt"

    if request.method == "POST":
        specification = request.form.get("specification", "")
        save_text(spec_path, specification)
        flash("仕様書を保存しました。")
        return redirect(url_for("project_detail", project_name=project_name))

    return render_template(
        "project_detail.html",
        project_name=project_name,
        specification=load_text(spec_path),
        implementation_plan=load_text(plan_path),
        latest_log=load_text(log_path),
    )


if __name__ == "__main__":
    PROJECTS_DIR.mkdir(parents=True, exist_ok=True)
    app.run(debug=True)
