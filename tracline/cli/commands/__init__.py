"""CLI commands for TracLine."""

from .init import init
from .task import add, update, delete, list_tasks, show
from .workflow import next_task, done
from .assign import assign
from .relationship import link
from .files import attach
from .logs import log
from .config import config_cmd
from .migrate import migrate
from .list_relations import list_relations
from .list_files import ls_files
from .trace import trace
from .monitor import monitor
from .github import github

# Member management commands
from .member import (
    add as member_add,
    update as member_update,
    delete as member_delete,
    show as member_show,
    list_members as member_list,
    change_position as member_change_position,
    change_leader as member_change_leader,
    team_structure as member_team_structure
)

# Project management commands 
from .project import (
    create as project_create,
    update as project_update,
    delete as project_delete,
    show as project_show,
    list_projects as project_list,
    add_members as project_add_members,
    remove_members as project_remove_members,
    members as project_members,
    settings as project_settings
)

# Project v2 commands - enhanced project management
from .project_v2 import (
    show_current_project as project_current,
    change_project as project_change
)

__all__ = [
    "init",
    "add",
    "update",
    "delete",
    "show",
    "list_tasks",
    "next_task",
    "done",
    "assign",
    "link",
    "attach",
    "log",
    "config_cmd",
    "migrate",
    "list_relations",
    "ls_files",
    "trace",
    "monitor",
    "github",
    # Member commands
    "member_add",
    "member_update",
    "member_delete",
    "member_show",
    "member_list",
    "member_change_position",
    "member_change_leader",
    "member_team_structure",
    # Project commands
    "project_create",
    "project_update",
    "project_delete", 
    "project_show",
    "project_list",
    "project_add_members",
    "project_remove_members",
    "project_members",
    "project_settings",
    # Project v2 commands
    "project_current",
    "project_change"
]