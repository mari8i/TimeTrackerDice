import logging
import urllib

from dataclasses import dataclass
from typing import List, Union

from django.contrib.auth.models import User
from lru import lazy_cache
from toggl.TogglPy import Toggl

TOGGL_URL = "https://www.toggl.com/api/v8"

logger = logging.getLogger(__name__)


@dataclass()
class TogglProject:
    id: int
    name: str


@dataclass()
class TogglTag:
    name: str


@dataclass()
class TogglWorkspace:
    id: int


class TogglInvalidCredentialsError(Exception):
    pass


class TogglConnectionError(Exception):
    pass


def toggl_exception_handler(func):
    def inner_function(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except urllib.error.HTTPError as e:
            if e.getcode() == 403:
                raise TogglInvalidCredentialsError()
            raise TogglConnectionError()

    return inner_function


def _get_toggl(user: User) -> Toggl:
    toggl = Toggl()
    toggl.setAPIKey(user.togglcredentials.api_key)
    return toggl


@lazy_cache(maxsize=128, expires=60)
@toggl_exception_handler
def _fetch_toggl_projects(user: User) -> List[TogglProject]:
    logger.info(f"Fetching toggl projects for user {user}")
    toggl = _get_toggl(user)
    default_workspace = _get_default_workspace(user)
    projects = toggl.request(f"{TOGGL_URL}/workspaces/{default_workspace.id}/projects")
    return [TogglProject(id=p["id"], name=p["name"]) for p in projects]


@lazy_cache(maxsize=128, expires=60)
@toggl_exception_handler
def _fetch_toggl_tags(user: User) -> List[TogglTag]:
    logger.info(f"Fetching toggl tags for user {user}")

    toggl = _get_toggl(user)
    default_workspace = _get_default_workspace(user)
    toggl_tags = toggl.request(f"{TOGGL_URL}/workspaces/{default_workspace.id}/tags")

    return [TogglTag(name=tag['name']) for tag in toggl_tags]


@lazy_cache(maxsize=128, expires=60)
@toggl_exception_handler
def _get_default_workspace(user: User) -> TogglWorkspace:
    logger.info(f"Fetching toggl default workspace for user {user}")
    toggl = _get_toggl(user)
    default_workspace = toggl.getWorkspaces()[0]
    return TogglWorkspace(id=default_workspace['id'])


class TogglService:

    def __init__(self, user: User):
        self.user = user
        self.toggl = _get_toggl(user)

    @toggl_exception_handler
    def test_api_key(self) -> None:
        toggl = _get_toggl(self.user)
        toggl.getWorkspaces()

    @toggl_exception_handler
    def start_time_entry(self, description: str, project_id: int,
                         tags: Union[List[str], None] = None):
        self.toggl.startTimeEntry(description, project_id, tags=tags)

    @toggl_exception_handler
    def stop_current_time_entry(self):
        current_timer = self.toggl.currentRunningTimeEntry()
        if current_timer and current_timer['data'] and current_timer['data']['id']:
            self.toggl.stopTimeEntry(current_timer['data']['id'])

    def find_project_by_id(self, project_id: int) -> Union[TogglProject, None]:
        projects = self.fetch_toggl_projects()

        try:
            return next(project for project in projects if project.id == project_id)
        except StopIteration:
            return None

    def find_project_name_by_id(self, project_id: int) -> Union[str, None]:
        prj = self.find_project_by_id(project_id)
        return prj.name if prj else None

    def find_project_id_by_name(self, project_name: str) -> Union[int, None]:
        prj = self.find_project_by_name(project_name)
        return prj.id if prj else None

    def find_project_by_name(self, project_name: str) -> Union[TogglProject, None]:
        projects = self.fetch_toggl_projects()

        try:
            return next(project for project in projects if project.name == project_name)
        except StopIteration:
            return None

    def fetch_toggl_projects(self) -> List[TogglProject]:
        return _fetch_toggl_projects(self.user)

    def fetch_toggl_tags(self) -> List[TogglTag]:
        return _fetch_toggl_tags(self.user)

    def _get_default_workspace(self) -> TogglWorkspace:
        return _get_default_workspace(self.user)
