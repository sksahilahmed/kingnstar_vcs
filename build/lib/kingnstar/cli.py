"""
CLI interface for Kingnstar VCS
Entry point for all kingnstar commands
"""

import click
import os
import sys
from kingnstar.repo import Repository


@click.group()
def cli():
    """Kingnstar - A Git-like Version Control System"""
    pass


@cli.command(name="start")
@click.option(
    "--dir",
    default=".",
    help="Directory to initialize repository in (default: current directory)",
)
def cmd_start(dir):
    """Initialize a new Kingnstar repository"""
    repo = Repository(work_dir=dir)
    result = repo.initialize()

    if result["success"]:
        if result.get("idempotent"):
            click.echo(click.style("✓ ", fg="green") + result["message"])
        else:
            click.echo(click.style("✓ ", fg="green") + result["message"])
    else:
        click.echo(click.style("✗ ", fg="red") + result["message"], err=True)
        raise SystemExit(1)


@cli.command(name="status")
@click.option(
    "--dir",
    default=".",
    help="Repository directory (default: current directory)",
)
def cmd_status(dir):
    """Show repository status"""
    repo = Repository(work_dir=dir)

    if not repo.is_initialized():
        click.echo(
            click.style("✗ ", fg="red") + f"Not a Kingnstar repository",
            err=True,
        )
        raise SystemExit(1)

    branch = repo.get_current_branch()
    commit = repo.get_current_commit()
    staged = repo.get_staged_files()

    click.echo(f"On branch: {click.style(branch, fg='cyan')}")
    if commit:
        click.echo(f"Current commit: {click.style(commit[:8], fg='yellow')}")
    else:
        click.echo("No commits yet")
    
    if staged:
        click.echo(f"\nStaged files ({len(staged)}):")
        for file in staged:
            click.echo(f"  {click.style('+', fg='green')} {file}")


@cli.command(name="add")
@click.argument("patterns", nargs=-1, required=True)
@click.option(
    "--dir",
    default=".",
    help="Repository directory (default: current directory)",
)
def cmd_add(patterns, dir):
    """Stage files for commit (supports * glob patterns)"""
    repo = Repository(work_dir=dir)

    if not repo.is_initialized():
        click.echo(
            click.style("✗ ", fg="red") + "Not a Kingnstar repository",
            err=True,
        )
        raise SystemExit(1)

    result = repo.add_files(list(patterns))

    if result["success"]:
        click.echo(click.style("✓ ", fg="green") + result["message"])
        for file in result.get("files", []):
            click.echo(f"  {click.style('+', fg='green')} {file}")
    else:
        click.echo(click.style("✗ ", fg="red") + result["message"], err=True)
        raise SystemExit(1)


@cli.command(name="commit")
@click.option(
    "-m",
    "--message",
    required=True,
    help="Commit message",
)
@click.option(
    "--dir",
    default=".",
    help="Repository directory (default: current directory)",
)
def cmd_commit(message, dir):
    """Create a commit from staged files"""
    repo = Repository(work_dir=dir)

    if not repo.is_initialized():
        click.echo(
            click.style("✗ ", fg="red") + "Not a Kingnstar repository",
            err=True,
        )
        raise SystemExit(1)

    result = repo.commit(message)

    if result["success"]:
        click.echo(click.style("✓ ", fg="green") + result["message"])
    else:
        click.echo(click.style("✗ ", fg="red") + result["message"], err=True)
        raise SystemExit(1)


@cli.command(name="branch")
@click.option(
    "--dir",
    default=".",
    help="Repository directory (default: current directory)",
)
def cmd_branch(dir):
    """List all branches"""
    repo = Repository(work_dir=dir)

    if not repo.is_initialized():
        click.echo(
            click.style("✗ ", fg="red") + "Not a Kingnstar repository",
            err=True,
        )
        raise SystemExit(1)

    result = repo.list_branches()

    if result["success"]:
        branches = result.get("branches", [])
        if not branches:
            click.echo("No branches found")
        else:
            for branch in branches:
                marker = click.style("* ", fg="green") if branch["current"] else "  "
                click.echo(f"{marker}{branch['name']}")
    else:
        click.echo(click.style("✗ ", fg="red") + result["message"], err=True)
        raise SystemExit(1)


@cli.command(name="new")
@click.argument("action")
@click.argument("branch_name")
@click.option(
    "--dir",
    default=".",
    help="Repository directory (default: current directory)",
)
def cmd_new_branch(action, branch_name, dir):
    """Create a new branch with password protection"""
    if action != "branch":
        click.echo(
            click.style("✗ ", fg="red") + f"Unknown action: {action}",
            err=True,
        )
        raise SystemExit(1)

    repo = Repository(work_dir=dir)

    if not repo.is_initialized():
        click.echo(
            click.style("✗ ", fg="red") + "Not a Kingnstar repository",
            err=True,
        )
        raise SystemExit(1)

    # Prompt for password
    password = click.prompt("Enter password", hide_input=True)
    password_confirm = click.prompt("Confirm password", hide_input=True)

    if password != password_confirm:
        click.echo(
            click.style("✗ ", fg="red") + "Passwords do not match",
            err=True,
        )
        raise SystemExit(1)

    result = repo.create_branch(branch_name, password)

    if result["success"]:
        click.echo(click.style("✓ ", fg="green") + result["message"])
    else:
        click.echo(click.style("✗ ", fg="red") + result["message"], err=True)
        raise SystemExit(1)


@cli.command(name="switch")
@click.argument("branch_name")
@click.argument("password", required=False)
@click.option(
    "--dir",
    default=".",
    help="Repository directory (default: current directory)",
)
def cmd_switch(branch_name, password, dir):
    """Switch to another branch (requires password)"""
    repo = Repository(work_dir=dir)

    if not repo.is_initialized():
        click.echo(
            click.style("✗ ", fg="red") + "Not a Kingnstar repository",
            err=True,
        )
        raise SystemExit(1)

    # If password not provided, prompt for it
    if not password:
        password = click.prompt("Enter branch password", hide_input=True)

    result = repo.switch_branch(branch_name, password)

    if result["success"]:
        click.echo(click.style("✓ ", fg="green") + result["message"])
    else:
        click.echo(click.style("✗ ", fg="red") + result["message"], err=True)
        raise SystemExit(1)


@cli.command(name="pull")
@click.argument("branch_name")
@click.argument("commit_id")
@click.option(
    "--dir",
    default=".",
    help="Repository directory (default: current directory)",
)
def cmd_pull(branch_name, commit_id, dir):
    """Pull a commit from another branch (cherry-pick with override)"""
    repo = Repository(work_dir=dir)

    if not repo.is_initialized():
        click.echo(
            click.style("✗ ", fg="red") + "Not a Kingnstar repository",
            err=True,
        )
        raise SystemExit(1)

    # Check for conflicts first
    result = repo.pull_commit(branch_name, commit_id)

    if result.get("requires_confirmation"):
        # Conflicts detected - ask for confirmation
        click.echo(click.style("⚠ ", fg="yellow") + result["message"])
        click.echo("Files to be overridden:")
        for conflict in result.get("conflicts", []):
            click.echo(f"  {click.style('!', fg='yellow')} {conflict}")
        
        confirm = click.confirm("Override files and pull commit?", default=False)
        
        if not confirm:
            click.echo("Pull cancelled")
            return

        # Execute pull with confirmation
        confirm_result = repo.pull_commit_confirm(commit_id)
        
        if confirm_result["success"]:
            click.echo(click.style("✓ ", fg="green") + confirm_result["message"])
            for file in confirm_result.get("files_updated", []):
                click.echo(f"  {click.style('+', fg='green')} {file}")
        else:
            click.echo(click.style("✗ ", fg="red") + confirm_result["message"], err=True)
            raise SystemExit(1)

    elif result["success"]:
        # No conflicts, pull succeeded
        click.echo(click.style("✓ ", fg="green") + result["message"])

    else:
        # Error
        click.echo(click.style("✗ ", fg="red") + result["message"], err=True)
        raise SystemExit(1)


@cli.command(name="go")
@click.argument("commit_id")
@click.option(
    "--dir",
    default=".",
    help="Repository directory (default: current directory)",
)
def cmd_go(commit_id, dir):
    """Checkout to a specific commit - restore working directory to that commit's state"""
    repo = Repository(work_dir=dir)

    if not repo.is_initialized():
        click.echo(
            click.style("✗ ", fg="red") + "Not a Kingnstar repository",
            err=True,
        )
        raise SystemExit(1)

    result = repo.checkout_commit(commit_id)

    if result["success"]:
        click.echo(click.style("✓ ", fg="green") + result["message"])
        click.echo(f"Checked out to commit: {commit_id}")
        if result.get("files_restored"):
            click.echo("Files restored:")
            for file in result["files_restored"]:
                click.echo(f"  {click.style('→', fg='cyan')} {file}")
    else:
        click.echo(click.style("✗ ", fg="red") + result["message"], err=True)
        raise SystemExit(1)


@cli.command(name="log")
@click.option("--branch", default=None, help="Branch to show log for (default: current)")
@click.option(
    "--dir",
    default=".",
    help="Repository directory (default: current directory)",
)
def cmd_log(branch, dir):
    """Show commit history"""
    repo = Repository(work_dir=dir)

    if not repo.is_initialized():
        click.echo(
            click.style("✗ ", fg="red") + "Not a Kingnstar repository",
            err=True,
        )
        raise SystemExit(1)

    result = repo.get_commit_history(branch)

    if result["success"]:
        if not result["commits"]:
            click.echo("No commits yet")
        else:
            for i, commit in enumerate(result["commits"]):
                click.echo(
                    click.style(commit["hash"], fg="yellow")
                    + f' {commit["message"]}'
                )
                if i < len(result["commits"]) - 1:
                    click.echo("  |")
    else:
        click.echo(click.style("✗ ", fg="red") + result.get("message", "Error"), err=True)
        raise SystemExit(1)


@cli.command(name="show")
@click.argument("commit_id")
@click.option(
    "--dir",
    default=".",
    help="Repository directory (default: current directory)",
)
def cmd_show(commit_id, dir):
    """Show commit details and files"""
    repo = Repository(work_dir=dir)

    if not repo.is_initialized():
        click.echo(
            click.style("✗ ", fg="red") + "Not a Kingnstar repository",
            err=True,
        )
        raise SystemExit(1)

    result = repo.show_commit(commit_id)

    if result["success"]:
        click.echo(click.style("commit ", fg="yellow") + result["commit"])
        click.echo(f"Message: {result['message']}")
        click.echo(f"Timestamp: {result['timestamp']}")
        click.echo(f"Parent: {result['parent']}")
        click.echo(f"\nFiles ({result['file_count']}):")
        for file in result["files"]:
            click.echo(f"  {click.style('+', fg='green')} {file}")
    else:
        click.echo(click.style("✗ ", fg="red") + result["message"], err=True)
        raise SystemExit(1)


@cli.command(name="reset")
@click.argument("patterns", nargs=-1)
@click.option(
    "--dir",
    default=".",
    help="Repository directory (default: current directory)",
)
def cmd_reset(patterns, dir):
    """Unstage files from commit"""
    repo = Repository(work_dir=dir)

    if not repo.is_initialized():
        click.echo(
            click.style("✗ ", fg="red") + "Not a Kingnstar repository",
            err=True,
        )
        raise SystemExit(1)

    result = repo.reset_files(list(patterns) if patterns else None)

    if result["success"]:
        click.echo(click.style("✓ ", fg="green") + result["message"])
        for file in result.get("unstaged", []):
            click.echo(f"  {click.style('-', fg='red')} {file}")
    else:
        click.echo(click.style("✗ ", fg="red") + result["message"], err=True)
        raise SystemExit(1)


@cli.command(name="diff")
@click.option(
    "--dir",
    default=".",
    help="Repository directory (default: current directory)",
)
def cmd_diff(dir):
    """Show changes since last commit"""
    repo = Repository(work_dir=dir)

    if not repo.is_initialized():
        click.echo(
            click.style("✗ ", fg="red") + "Not a Kingnstar repository",
            err=True,
        )
        raise SystemExit(1)

    result = repo.get_changes()

    if result["success"]:
        if not result["changed"]:
            click.echo("No changes")
        else:
            click.echo(f"Changed files ({len(result['changed'])}):")
            for change in result["changed"]:
                if change["status"] == "modified":
                    symbol = click.style("M", fg="yellow")
                elif change["status"] == "new":
                    symbol = click.style("+", fg="green")
                else:  # deleted
                    symbol = click.style("-", fg="red")

                click.echo(f"  {symbol} {change['file']}")
    else:
        click.echo(click.style("✗ ", fg="red") + result.get("message", "Error"), err=True)
        raise SystemExit(1)


@cli.command(name="rm")
@click.argument("patterns", nargs=-1, required=True)
@click.option(
    "--dir",
    default=".",
    help="Repository directory (default: current directory)",
)
def cmd_rm(patterns, dir):
    """Remove tracked files"""
    repo = Repository(work_dir=dir)

    if not repo.is_initialized():
        click.echo(
            click.style("✗ ", fg="red") + "Not a Kingnstar repository",
            err=True,
        )
        raise SystemExit(1)

    result = repo.remove_files(list(patterns))

    if result["success"]:
        click.echo(click.style("✓ ", fg="green") + result["message"])
        for file in result.get("removed", []):
            click.echo(f"  {click.style('rm', fg='red')} {file}")
    else:
        click.echo(click.style("✗ ", fg="red") + result["message"], err=True)
        raise SystemExit(1)


def main():
    """Main entry point for kingnstar CLI"""
    try:
        cli()
    except Exception as e:
        click.echo(click.style(f"Error: {str(e)}", fg="red"), err=True)
        raise SystemExit(1)


if __name__ == "__main__":
    main()
