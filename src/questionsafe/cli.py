import typer
from rich.console import Console

app = typer.Typer()
console = Console()


@app.callback(invoke_without_command=True)
def _callback():  # pyright: ignore[reportUnusedFunction]
    """
    A Moodle Quiz Composer
    """


@app.command()
def init():
    raise NotImplementedError


@app.command()
def build():
    raise NotImplementedError


@app.command()
def validate():
    raise NotImplementedError


@app.command()
def preview():
    raise NotImplementedError


if __name__ == "__main__":
    app()
