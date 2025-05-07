import os
import sys
import logging
import json
from pathlib import Path
from typing import Iterable, Optional, Dict, List
import asana

import mcp.types as types

project_root = os.path.abspath(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
)
sys.path.insert(0, project_root)
sys.path.insert(0, os.path.join(project_root, "src"))

from mcp.types import Resource, TextContent
from mcp.server.lowlevel.helper_types import ReadResourceContents
from mcp.server import NotificationOptions, Server
from mcp.server.models import InitializationOptions

from src.utils.asana.util import authenticate_and_save_credentials, get_credentials

SERVICE_NAME = Path(__file__).parent.name

SCOPES = [
    "attachments:write",
    "goals:read",
    "project_templates:read",
    "projects:read",
    "projects:write",
    "projects:delete",
    "stories:read",
    "tasks:read",
    "tasks:write",
    "tasks:delete",
    "users:read",
    "workspaces:read",
]

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(SERVICE_NAME)


class AsanaClient:
    """Client for interacting with the Asana API."""

    def __init__(self, access_token: str):
        """Initialize the Asana client with an access token."""
        configuration = asana.Configuration()
        configuration.access_token = access_token
        self.api_client = asana.ApiClient(configuration)

        # Initialize API instances
        self.users_api = asana.UsersApi(self.api_client)
        self.workspaces_api = asana.WorkspacesApi(self.api_client)
        self.projects_api = asana.ProjectsApi(self.api_client)
        self.tasks_api = asana.TasksApi(self.api_client)
        self.stories_api = asana.StoriesApi(self.api_client)
        self.tags_api = asana.TagsApi(self.api_client)
        self.sections_api = asana.SectionsApi(self.api_client)
        self.attachments_api = asana.AttachmentsApi(self.api_client)

    def get_me(self) -> Dict:
        """Get the current user's information."""
        try:
            # Try with minimal options
            return self.users_api.get_user("me", {})
        except Exception as e:
            # Print the full exception details
            import traceback

            print(f"Error type: {type(e)}")
            print(f"Error message: {str(e)}")
            print(f"Traceback: {traceback.format_exc()}")

    def get_workspaces(self) -> List[Dict]:
        """Get all workspaces accessible to the user."""
        opts = {}
        workspaces = self.workspaces_api.get_workspaces(opts)
        return list(workspaces)

    def get_projects(self, workspace_id: str) -> List[Dict]:
        """Get all projects in a workspace."""
        opts = {}
        projects = self.projects_api.get_projects_for_workspace(workspace_id, opts)
        return list(projects)

    def get_project(self, project_id: str) -> Dict:
        """Get a specific project by ID."""
        opts = {}
        return self.projects_api.get_project(project_id, opts)

    def get_tasks(self, project_id: str) -> List[Dict]:
        """Get all tasks in a project."""
        opts = {}
        tasks = self.tasks_api.get_tasks_for_project(project_id, opts)
        return list(tasks)

    def get_task(self, task_id: str) -> Dict:
        """Get a specific task by ID."""
        opts = {}
        return self.tasks_api.get_task(task_id, opts)

    def create_task(
        self, name: str, project_id: str, notes: str, completed: bool = False, **kwargs
    ) -> Dict:
        """Create a new task in a project."""
        task_data = {
            "data": {
                "name": name,
                "projects": [project_id],
                "completed": completed,
                "notes": notes,
                **kwargs,
            }
        }

        opts = {
            "opt_fields": "name,notes,assignee,assignee.name,completed,completed_at,due_on,projects,projects.name,workspace,workspace.name"
        }

        try:
            return self.tasks_api.create_task(task_data, opts)
        except asana.rest.ApiException as e:
            logger.error(f"Exception when calling TasksApi->create_task: {str(e)}")
            raise

    def update_task(self, task_id: str, **kwargs) -> Dict:
        """Update a task."""
        task_data = {
            "data": {
                "name": kwargs.get("name"),
                "notes": kwargs.get("notes"),
            }
        }

        # Remove None values from the inner data dictionary
        task_data["data"] = {
            k: v for k, v in task_data["data"].items() if v is not None
        }

        opts = {}
        return self.tasks_api.update_task(task_data, task_id, opts)

    def delete_task(self, task_id: str) -> Dict:
        """Delete a task."""
        return self.tasks_api.delete_task(task_id)

    def get_users(self, workspace_id: str) -> List[Dict]:
        """Get all users in a workspace."""
        opts = {}
        users = self.users_api.get_users_for_workspace(workspace_id, opts)
        return list(users)

    def get_user(self, user_id: str) -> Dict:
        """Get a specific user by ID."""
        opts = {}
        return self.users_api.get_user(user_id, opts)

    def duplicate_task(self, task_id: str, name: str = None) -> Dict:
        """Duplicate an existing task."""
        # First get the original task details
        original_task = self.get_task(task_id)

        # Extract the task data from the response
        task_data = original_task.get("data", {})

        # Create the duplicate task data
        duplicate_data = {
            "data": {
                "name": name or task_data.get("name", ""),
                "notes": task_data.get("notes"),
                "assignee": task_data.get("assignee", {}).get("gid"),
                "due_on": task_data.get("due_on"),
                "completed": task_data.get("completed"),
                "projects": [p["gid"] for p in task_data.get("projects", [])],
                "parent": task_data.get("parent", {}).get("gid"),
                "memberships": task_data.get("memberships", []),
                "tags": [t["gid"] for t in task_data.get("tags", [])],
            }
        }

        # Remove None values from the inner data dictionary
        duplicate_data["data"] = {
            k: v for k, v in duplicate_data["data"].items() if v is not None
        }

        opts = {}
        return self.tasks_api.duplicate_task(duplicate_data, task_id, opts)

    def add_follower_to_task(self, task_id: str, user_id: str) -> Dict:
        """Add a follower to a task."""
        follower_data = {"data": {"followers": [user_id]}}
        opts = {}
        return self.tasks_api.add_followers_for_task(follower_data, task_id, opts)

    def remove_follower_from_task(self, task_id: str, user_id: str) -> Dict:
        """Remove a follower from a task."""
        follower_data = {"data": {"followers": [user_id]}}
        opts = {}
        return self.tasks_api.remove_follower_for_task(follower_data, task_id, opts)

    def mark_task_complete(self, task_id: str) -> Dict:
        """Mark a task as complete."""
        task_data = {"data": {"completed": True}}
        opts = {}
        return self.tasks_api.update_task(task_data, task_id, opts)

    def mark_task_incomplete(self, task_id: str) -> Dict:
        """Mark a task as incomplete."""
        task_data = {"data": {"completed": False}}
        opts = {}
        return self.tasks_api.update_task(task_data, task_id, opts)

    def add_subtask(self, parent_task_id: str, name: str, **kwargs) -> Dict:
        """Add a subtask to an existing task."""
        subtask_data = {
            "data": {
                "name": name,
                "notes": kwargs.get("notes"),
                "assignee": kwargs.get("assignee"),
                "due_on": kwargs.get("due_on"),
            }
        }
        parent_task_gid = parent_task_id

        # Remove None values from the inner data dictionary
        subtask_data["data"] = {
            k: v for k, v in subtask_data["data"].items() if v is not None
        }

        opts = {}
        return self.tasks_api.create_subtask_for_task(
            subtask_data, parent_task_gid, opts
        )

    def assign_task(self, task_id: str, user_id: str) -> Dict:
        """Assign a task to a user."""
        task_data = {"data": {"assignee": user_id}}
        opts = {}
        return self.tasks_api.update_task(task_data, task_id, opts)

    def unassign_task(self, task_id: str) -> Dict:
        """Remove the assignee from a task."""
        task_data = {"data": {"assignee": None}}
        opts = {}
        return self.tasks_api.update_task(task_data, task_id, opts)

    def add_task_to_project(self, task_id: str, project_id: str) -> Dict:
        """Add an existing task to a project."""
        project_data = {"data": {"project": project_id}}

        return self.tasks_api.add_project_for_task(project_data, task_id)

    def remove_task_from_project(self, task_id: str, project_id: str) -> Dict:
        """Remove a task from a project."""
        project_data = {"data": {"project": project_id}}
        return self.tasks_api.remove_project_for_task(project_data, task_id)

    def create_project(self, workspace_id: str, name: str, **kwargs) -> Dict:
        """Create a new project in a workspace."""
        project_data = {"data": {"name": name, **kwargs}}

        # Remove None values
        project_data["data"] = {
            k: v for k, v in project_data["data"].items() if v is not None
        }

        opts = {
            "opt_fields": "name,notes,owner,owner.name,current_status,current_status.text,created_at,modified_at,due_date,public,members,members.name,workspace,workspace.name"
        }
        return self.projects_api.create_project_for_workspace(
            project_data, workspace_id, opts
        )

    def update_project(self, project_id: str, **kwargs) -> Dict:
        """Update details of an existing project."""
        project_data = {
            "data": {
                "name": kwargs.get("name"),
                "notes": kwargs.get("notes"),
                "color": kwargs.get("color"),
                "due_date": kwargs.get("due_date"),
                "public": kwargs.get("public"),
                "owner": kwargs.get("owner"),
                "current_status": kwargs.get("current_status"),
            }
        }

        # Remove None values from the inner data dictionary
        project_data["data"] = {
            k: v for k, v in project_data["data"].items() if v is not None
        }

        opts = {
            "opt_fields": "name,notes,owner,owner.name,current_status,current_status.text,created_at,modified_at,due_date,public,members,members.name,workspace,workspace.name"
        }
        return self.projects_api.update_project(project_data, project_id, opts)

    def create_section(self, project_id: str, name: str) -> Dict:
        """Create a new section in a project"""
        opts = {
            "body": {"data": {"name": name}},
            "opt_fields": "created_at,name,project,project.name,projects,projects.name",
        }
        return self.sections_api.create_section_for_project(project_id, opts)

    def add_task_to_section(
        self,
        section_id: str,
        task_id: str,
        insert_before: str = None,
        insert_after: str = None,
    ) -> Dict:
        """Add a task to a specific section.

        Args:
            section_id: The ID of the section to add the task to
            task_id: The ID of the task to add
            insert_before: Optional task ID to insert before
            insert_after: Optional task ID to insert after

        Returns:
            Dict containing the updated task details
        """
        data = {"task": task_id}
        if insert_before:
            data["insert_before"] = insert_before
        if insert_after:
            data["insert_after"] = insert_after

        opts = {"body": {"data": data}}

        return self.sections_api.add_task_for_section(section_id, opts)

    def get_sections(
        self, project_id: str, section_name: str = None, limit: int = 50
    ) -> List[Dict]:
        """Get sections in a project, optionally filtered by name.

        Args:
            project_id: The ID of the project to get sections from
            section_name: Optional name to filter sections by
            limit: Maximum number of sections to return (default: 50)

        Returns:
            List of section details matching the criteria
        """
        opts = {
            "limit": int(limit),
            "opt_fields": "created_at,name,offset,path,project,project.name,projects,projects.name,uri",
        }

        sections = self.sections_api.get_sections_for_project(project_id, opts)
        logger.info(f"Sections: {sections}")
        sections_list = list(sections)

        if section_name:
            # Filter sections by name (case-insensitive)
            sections_list = [
                section
                for section in sections_list
                if section.get("name", "").lower() == section_name.lower()
            ]

        return sections_list

    def delete_section(self, section_id: str) -> Dict:
        """Delete a specific section.

        Args:
            section_id: The ID of the section to delete

        Returns:
            Empty data block if successful

        Note:
            - Section must be empty to be deleted
            - Last remaining section cannot be deleted
        """
        return self.sections_api.delete_section(section_id)

    def create_tag(
        self, workspace_id: str, name: str, color: str = None, notes: str = None
    ) -> Dict:
        """Create a new tag in a workspace or organization.

        Args:
            workspace_id: The ID of the workspace or organization to create the tag in
            name: The name of the tag
            color: Optional color for the tag
            notes: Optional notes for the tag

        Returns:
            Dict containing the created tag details

        Note:
            - Tag must be created in a specific workspace/organization
            - This cannot be changed once set
        """
        tag_data = {"data": {"name": name, "workspace": workspace_id}}

        if color:
            tag_data["data"]["color"] = color
        if notes:
            tag_data["data"]["notes"] = notes

        opts = {
            "opt_fields": "color,created_at,followers,followers.name,name,notes,permalink_url,workspace,workspace.name"
        }

        return self.tags_api.create_tag(tag_data, opts)

    def get_tags(
        self, workspace_id: str, tag_name: str = None, limit: int = 50
    ) -> List[Dict]:
        """Get tags in a workspace, optionally filtered by name.

        Args:
            workspace_id: The ID of the workspace to get tags from
            tag_name: Optional name to filter tags by
            limit: Maximum number of tags to return (default: 50)

        Returns:
            List of tag details matching the criteria
        """
        opts = {
            "workspace": workspace_id,
            "limit": limit,
            "opt_fields": "color,created_at,followers,followers.name,name,notes,offset,path,permalink_url,uri,workspace,workspace.name",
        }

        tags = self.tags_api.get_tags(opts)
        tags_list = list(tags)

        if tag_name:
            # Filter tags by name (case-insensitive)
            tags_list = [
                tag
                for tag in tags_list
                if tag.get("name", "").lower() == tag_name.lower()
            ]

        return tags_list

    def add_tag_to_task(self, task_id: str, tag_id: str) -> Dict:
        """Add a tag to a task.

        Args:
            task_id: The ID of the task to add the tag to
            tag_id: The ID of the tag to add

        Returns:
            Empty data block if successful
        """
        tag_data = {"data": {"tag": tag_id}}

        return self.tasks_api.add_tag_for_task(tag_data, task_id)

    def remove_tag_from_task(self, task_id: str, tag_id: str) -> Dict:
        """Remove a tag from a task.

        Args:
            task_id: The ID of the task to remove the tag from
            tag_id: The ID of the tag to remove

        Returns:
            Empty data block if successful
        """
        tag_data = {"data": {"tag": tag_id}}

        return self.tasks_api.remove_tag_for_task(tag_data, task_id)

    def create_attachment(
        self,
        parent_id: str,
        file_path: str = None,
        url: str = None,
        name: str = None,
        connect_to_app: bool = False,
    ) -> Dict:
        """Create an attachment for a task or other object.

        Args:
            parent_id: The ID of the parent object (task, project, etc.)
            file_path: Path to the file to upload
            url: URL of the external resource to attach
            name: Name for the attachment
            connect_to_app: Whether to connect the attachment to an app

        Returns:
            Dict containing the created attachment details

        Note:
            - File size limit is 100MB
            - Cannot attach files from third-party services (Dropbox, Box, Vimeo, Google Drive)
            - For non-ASCII filenames, use URL-encoded names
        """
        opts = {
            "parent": parent_id,
            "opt_fields": "connected_to_app,created_at,download_url,host,name,parent,parent.created_by,parent.name,parent.resource_subtype,permanent_url,resource_subtype,size,view_url",
            "connect_to_app": connect_to_app,
        }

        if url:
            opts["url"] = url
            opts["resource_subtype"] = "external"

        if name:
            opts["name"] = name

        return self.attachments_api.create_attachment_for_object(opts)


async def create_asana_client(user_id: str, api_key: str = None) -> AsanaClient:
    """Create an authorized Asana API client."""
    access_token = await get_credentials(user_id, SERVICE_NAME, api_key=api_key)
    return AsanaClient(access_token)


def create_server(user_id: str, api_key: str = None) -> Server:
    """Initialize and configure the Asana MCP server."""
    server = Server("asana-server")

    server.user_id = user_id
    server.api_key = api_key
    server._asana_client = None

    async def _get_asana_client() -> AsanaClient:
        """Get or create an Asana client."""
        if not server._asana_client:
            server._asana_client = await create_asana_client(
                server.user_id, server.api_key
            )
        return server._asana_client

    @server.list_resources()
    async def handle_list_resources(
        cursor: Optional[str] = None,
    ) -> list[Resource]:
        """List Asana resources (workspaces, projects, tasks, tags, attachments)"""
        logger.info(
            f"Listing resources for user: {server.user_id} with cursor: {cursor}"
        )

        asana = await _get_asana_client()
        try:
            resources = []

            # List all workspaces
            workspaces = asana.get_workspaces()
            for workspace in workspaces:
                resources.append(
                    Resource(
                        uri=f"asana://workspace/{workspace['gid']}",
                        mimeType="application/json",
                        name=f"Workspace: {workspace['name']}",
                        description="Asana workspace",
                    )
                )

            # List all projects in each workspace
            for workspace in workspaces:
                projects = asana.get_projects(workspace["gid"])
                for project in projects:
                    resources.append(
                        Resource(
                            uri=f"asana://project/{project['gid']}",
                            mimeType="application/json",
                            name=f"Project: {project['name']}",
                            description=f"Project in workspace {workspace['name']}",
                        )
                    )

            # List all tasks in each project
            for workspace in workspaces:
                projects = asana.get_projects(workspace["gid"])
                for project in projects:
                    tasks = asana.get_tasks(project["gid"])
                    for task in tasks:
                        resources.append(
                            Resource(
                                uri=f"asana://task/{task['gid']}",
                                mimeType="application/json",
                                name=f"Task: {task['name']}",
                                description=f"Task in project {project['name']}",
                            )
                        )

            # List all tags in each workspace
            for workspace in workspaces:
                tags = asana.get_tags(workspace["gid"])
                for tag in tags:
                    resources.append(
                        Resource(
                            uri=f"asana://tag/{tag['gid']}",
                            mimeType="application/json",
                            name=f"Tag: {tag['name']}",
                            description=f"Tag in workspace {workspace['name']}",
                        )
                    )

            # List all attachments for each task
            for workspace in workspaces:
                projects = asana.get_projects(workspace["gid"])
                for project in projects:
                    tasks = asana.get_tasks(project["gid"])
                    for task in tasks:
                        # Note: We'll need to get attachments for each task
                        # This is a placeholder as we need to implement get_attachments_for_task
                        resources.append(
                            Resource(
                                uri=f"asana://task/{task['gid']}/attachments",
                                mimeType="application/json",
                                name=f"Attachments for Task: {task['name']}",
                                description=f"Attachments in task {task['name']}",
                            )
                        )

            return resources

        except Exception as e:
            logger.error(f"Error listing Asana resources: {e}")
            return []

    @server.read_resource()
    async def handle_read_resource(uri: str) -> Iterable[ReadResourceContents]:
        """Read a resource from Asana by URI"""
        logger.info(f"Reading resource: {uri} for user: {server.user_id}")

        asana = await _get_asana_client()
        uri = str(uri)
        try:
            if uri.startswith("asana://workspace/"):
                workspace_id = uri.replace("asana://workspace/", "")
                workspace = asana.get_workspaces()
                workspace = next(
                    (w for w in workspace if w["gid"] == workspace_id), None
                )
                if workspace:
                    return [
                        ReadResourceContents(
                            content=json.dumps(workspace, indent=2),
                            mime_type="application/json",
                        )
                    ]
            elif uri.startswith("asana://project/"):
                project_id = uri.replace("asana://project/", "")
                project = asana.get_project(project_id)
                return [
                    ReadResourceContents(
                        content=json.dumps(project, indent=2),
                        mime_type="application/json",
                    )
                ]
            elif uri.startswith("asana://task/"):
                if "/attachments" in uri:
                    task_id = uri.replace("asana://task/", "").replace(
                        "/attachments", ""
                    )
                    # Note: We'll need to implement get_attachments_for_task
                    # For now, return an empty list
                    return [
                        ReadResourceContents(
                            content=json.dumps({"attachments": []}, indent=2),
                            mime_type="application/json",
                        )
                    ]
                else:
                    task_id = uri.replace("asana://task/", "")
                    task = asana.get_task(task_id)
                    return [
                        ReadResourceContents(
                            content=json.dumps(task, indent=2),
                            mime_type="application/json",
                        )
                    ]
            elif uri.startswith("asana://tag/"):
                tag_id = uri.replace("asana://tag/", "")
                # Note: We'll need to implement get_tag
                # For now, return a placeholder
                return [
                    ReadResourceContents(
                        content=json.dumps(
                            {"gid": tag_id, "name": "Tag Name"}, indent=2
                        ),
                        mime_type="application/json",
                    )
                ]

            raise ValueError(f"Unsupported resource URI: {uri}")

        except Exception as e:
            logger.error(f"Error reading Asana resource: {e}")
            return [
                ReadResourceContents(
                    content=json.dumps({"error": str(e)}),
                    mime_type="application/json",
                )
            ]

    @server.list_tools()
    async def handle_list_tools() -> list[types.Tool]:
        """Return a list of available Asana tools."""
        return [
            types.Tool(
                name="get_me",
                description="Get the current user's information",
                inputSchema={"type": "object", "properties": {}},
                outputSchema={
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Array of JSON strings containing the operation results",
                    "examples": [
                        '[{"status":"success","data":{"gid":"12345","name":"John Doe","email":"john@example.com"}}]'
                    ],
                },
            ),
            types.Tool(
                name="get_workspaces",
                description="Get all workspaces accessible to the user",
                inputSchema={"type": "object", "properties": {}},
                outputSchema={
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Array of JSON strings containing the operation results",
                    "examples": [
                        '[{"status":"success","data":[{"gid":"12345","name":"My Workspace"}]}]'
                    ],
                },
            ),
            types.Tool(
                name="get_projects",
                description="Get all projects in a workspace",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "workspace_id": {
                            "type": "string",
                            "description": "The ID of the workspace",
                        }
                    },
                    "required": ["workspace_id"],
                },
                outputSchema={
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Array of JSON strings containing the operation results",
                    "examples": [
                        '[{"status":"success","data":[{"gid":"12345","name":"My Project"}]}]'
                    ],
                },
            ),
            types.Tool(
                name="get_project",
                description="Get a specific project by ID",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "project_id": {
                            "type": "string",
                            "description": "The ID of the project",
                        }
                    },
                    "required": ["project_id"],
                },
                outputSchema={
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Array of JSON strings containing the operation results",
                    "examples": [
                        '[{"status":"success","data":{"gid":"12345","name":"My Project"}}]'
                    ],
                },
            ),
            types.Tool(
                name="create_project",
                description="Create a new project in a workspace",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "workspace_id": {
                            "type": "string",
                            "description": "The ID of the workspace",
                        },
                        "name": {
                            "type": "string",
                            "description": "The name of the new project",
                        },
                        "notes": {
                            "type": "string",
                            "description": "Optional notes for the project",
                        },
                        "color": {
                            "type": "string",
                            "description": "Optional color of the project",
                        },
                        "due_date": {
                            "type": "string",
                            "description": "Optional due date (YYYY-MM-DD)",
                        },
                    },
                    "required": ["workspace_id", "name"],
                },
                outputSchema={
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Array of JSON strings containing the operation results",
                    "examples": [
                        '[{"status":"success","data":{"gid":"12345","name":"New Project"}}]'
                    ],
                },
            ),
            types.Tool(
                name="get_tasks",
                description="Get all tasks in a project",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "project_id": {
                            "type": "string",
                            "description": "The ID of the project",
                        }
                    },
                    "required": ["project_id"],
                },
                outputSchema={
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Array of JSON strings containing the operation results",
                    "examples": [
                        '[{"status":"success","data":[{"gid":"12345","name":"My Task"}]}]'
                    ],
                },
            ),
            types.Tool(
                name="get_task",
                description="Get a specific task by ID",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "task_id": {
                            "type": "string",
                            "description": "The ID of the task",
                        }
                    },
                    "required": ["task_id"],
                },
                outputSchema={
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Array of JSON strings containing the operation results",
                    "examples": [
                        '[{"status":"success","data":{"gid":"12345","name":"Retrieved Task"}}]'
                    ],
                },
            ),
            types.Tool(
                name="create_task",
                description="Create a new task in a project",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "name": {
                            "type": "string",
                            "description": "The name of the new task",
                        },
                        "project_id": {
                            "type": "string",
                            "description": "The ID of the project",
                        },
                        "notes": {
                            "type": "string",
                            "description": "Optional notes for the task",
                        },
                        "assignee": {
                            "type": "string",
                            "description": "Optional assignee ID",
                        },
                        "due_on": {
                            "type": "string",
                            "description": "Optional due date (YYYY-MM-DD)",
                        },
                        "completed": {
                            "type": "boolean",
                            "description": "Whether the task is completed",
                        },
                    },
                    "required": ["name", "project_id", "completed", "notes"],
                },
                outputSchema={
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Array of JSON strings containing the operation results",
                    "examples": [
                        '[{"status":"success","data":{"gid":"12345","name":"New Task"}}]'
                    ],
                },
            ),
            types.Tool(
                name="update_task",
                description="Update a task",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "task_id": {
                            "type": "string",
                            "description": "The ID of the task",
                        },
                        "name": {
                            "type": "string",
                            "description": "The new name of the task",
                        },
                        "notes": {
                            "type": "string",
                            "description": "New notes for the task",
                        },
                    },
                    "required": ["task_id"],
                },
                outputSchema={
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Array of JSON strings containing the operation results",
                    "examples": [
                        '[{"status":"success","data":{"gid":"12345","name":"Updated Task"}}]'
                    ],
                },
            ),
            types.Tool(
                name="delete_task",
                description="Delete a task",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "task_id": {
                            "type": "string",
                            "description": "The ID of the task to delete",
                        }
                    },
                    "required": ["task_id"],
                },
                outputSchema={
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Array of JSON strings containing the operation results",
                    "examples": ['[{"status":"success","data":{}}]'],
                },
            ),
            types.Tool(
                name="get_users",
                description="Get all users in a workspace",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "workspace_id": {
                            "type": "string",
                            "description": "The ID of the workspace",
                        }
                    },
                    "required": ["workspace_id"],
                },
                outputSchema={
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Array of JSON strings containing the operation results",
                    "examples": [
                        '[{"status":"success","data":[{"gid":"12345","name":"John Doe"}]}]'
                    ],
                },
            ),
            types.Tool(
                name="get_user",
                description="Get a specific user by ID",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "user_id": {
                            "type": "string",
                            "description": "The ID of the user",
                        }
                    },
                    "required": ["user_id"],
                },
                outputSchema={
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Array of JSON strings containing the operation results",
                    "examples": [
                        '[{"status":"success","data":{"gid":"12345","name":"John Doe"}}]'
                    ],
                },
            ),
            types.Tool(
                name="duplicate_task",
                description="Duplicate an existing task",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "task_id": {
                            "type": "string",
                            "description": "The ID of the task to duplicate",
                        },
                        "name": {
                            "type": "string",
                            "description": "Optional new name for the duplicated task",
                        },
                    },
                    "required": ["task_id"],
                },
                outputSchema={
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Array of JSON strings containing the operation results",
                    "examples": [
                        '[{"status":"success","data":{"gid":"12345","name":"Duplicated Task"}}]'
                    ],
                },
            ),
            types.Tool(
                name="add_follower_to_task",
                description="Add a follower to a task",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "task_id": {
                            "type": "string",
                            "description": "The ID of the task",
                        },
                        "user_id": {
                            "type": "string",
                            "description": "The ID of the user to add as follower",
                        },
                    },
                    "required": ["task_id", "user_id"],
                },
                outputSchema={
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Array of JSON strings containing the operation results",
                    "examples": [
                        '[{"status":"success","data":{"gid":"12345","followers":[{"gid":"67890"}]}}]'
                    ],
                },
            ),
            types.Tool(
                name="remove_follower_from_task",
                description="Remove a follower from a task",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "task_id": {
                            "type": "string",
                            "description": "The ID of the task",
                        },
                        "user_id": {
                            "type": "string",
                            "description": "The ID of the user to remove as follower",
                        },
                    },
                    "required": ["task_id", "user_id"],
                },
                outputSchema={
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Array of JSON strings containing the operation results",
                    "examples": [
                        '[{"status":"success","data":{"gid":"12345","followers":[]}}]'
                    ],
                },
            ),
            types.Tool(
                name="mark_task_complete",
                description="Mark a task as complete",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "task_id": {
                            "type": "string",
                            "description": "The ID of the task",
                        }
                    },
                    "required": ["task_id"],
                },
                outputSchema={
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Array of JSON strings containing the operation results",
                    "examples": [
                        '[{"status":"success","data":{"gid":"12345","completed":true}}]'
                    ],
                },
            ),
            types.Tool(
                name="mark_task_incomplete",
                description="Mark a task as incomplete",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "task_id": {
                            "type": "string",
                            "description": "The ID of the task",
                        }
                    },
                    "required": ["task_id"],
                },
                outputSchema={
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Array of JSON strings containing the operation results",
                    "examples": [
                        '[{"status":"success","data":{"gid":"12345","completed":false}}]'
                    ],
                },
            ),
            types.Tool(
                name="add_subtask",
                description="Add a subtask to an existing task",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "parent_task_id": {
                            "type": "string",
                            "description": "The ID of the parent task",
                        },
                        "name": {
                            "type": "string",
                            "description": "The name of the subtask",
                        },
                        "notes": {
                            "type": "string",
                            "description": "Optional notes for the subtask",
                        },
                        "assignee": {
                            "type": "string",
                            "description": "Optional assignee ID",
                        },
                        "due_on": {
                            "type": "string",
                            "description": "Optional due date (YYYY-MM-DD)",
                        },
                    },
                    "required": ["parent_task_id", "name"],
                },
                outputSchema={
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Array of JSON strings containing the operation results",
                    "examples": [
                        '[{"status":"success","data":{"gid":"12345","name":"New Subtask"}}]'
                    ],
                },
            ),
            types.Tool(
                name="assign_task",
                description="Assign a task to a user",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "task_id": {
                            "type": "string",
                            "description": "The ID of the task",
                        },
                        "user_id": {
                            "type": "string",
                            "description": "The ID of the user to assign",
                        },
                    },
                    "required": ["task_id", "user_id"],
                },
                outputSchema={
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Array of JSON strings containing the operation results",
                    "examples": [
                        '[{"status":"success","data":{"gid":"12345","assignee":{"gid":"67890"}}}]'
                    ],
                },
            ),
            types.Tool(
                name="unassign_task",
                description="Remove the assignee from a task",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "task_id": {
                            "type": "string",
                            "description": "The ID of the task",
                        }
                    },
                    "required": ["task_id"],
                },
                outputSchema={
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Array of JSON strings containing the operation results",
                    "examples": [
                        '[{"status":"success","data":{"gid":"12345","assignee":null}}]'
                    ],
                },
            ),
            types.Tool(
                name="add_task_to_project",
                description="Add an existing task to a project",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "task_id": {
                            "type": "string",
                            "description": "The ID of the task",
                        },
                        "project_id": {
                            "type": "string",
                            "description": "The ID of the project",
                        },
                    },
                    "required": ["task_id", "project_id"],
                },
                outputSchema={
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Array of JSON strings containing the operation results",
                    "examples": [
                        '[{"status":"success","data":{"gid":"12345","projects":[{"gid":"67890"}]}}]'
                    ],
                },
            ),
            types.Tool(
                name="remove_task_from_project",
                description="Remove a task from a project",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "task_id": {
                            "type": "string",
                            "description": "The ID of the task",
                        },
                        "project_id": {
                            "type": "string",
                            "description": "The ID of the project",
                        },
                    },
                    "required": ["task_id", "project_id"],
                },
                outputSchema={
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Array of JSON strings containing the operation results",
                    "examples": [
                        '[{"status":"success","data":{"gid":"12345","projects":[]}}]'
                    ],
                },
            ),
            types.Tool(
                name="update_project",
                description="Update details of an existing project",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "project_id": {
                            "type": "string",
                            "description": "The ID of the project to update",
                        },
                        "name": {
                            "type": "string",
                            "description": "New name for the project",
                        },
                        "notes": {
                            "type": "string",
                            "description": "New notes for the project",
                        },
                        "color": {
                            "type": "string",
                            "description": "New color for the project",
                        },
                        "due_date": {
                            "type": "string",
                            "description": "New due date (YYYY-MM-DD)",
                        },
                        "public": {
                            "type": "boolean",
                            "description": "Whether the project is public",
                        },
                        "owner": {
                            "type": "string",
                            "description": "New owner ID",
                        },
                        "current_status": {
                            "type": "string",
                            "description": "New status for the project",
                        },
                    },
                    "required": ["project_id"],
                },
                outputSchema={
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Array of JSON strings containing the operation results",
                    "examples": [
                        '[{"status":"success","data":{"gid":"12345","name":"Updated Project"}}]'
                    ],
                },
            ),
            types.Tool(
                name="create_section",
                description="Create a new section in a project",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "project_id": {
                            "type": "string",
                            "description": "The ID of the project to create the section in",
                        },
                        "name": {
                            "type": "string",
                            "description": "The name of the section to create",
                        },
                    },
                    "required": ["project_id", "name"],
                },
                outputSchema={
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Array of JSON strings containing the operation results",
                    "examples": [
                        '[{"status":"success","data":{"gid":"12345","name":"New Section","project":{"gid":"67890","name":"My Project"}}}]'
                    ],
                },
            ),
            types.Tool(
                name="add_task_to_section",
                description="Add a task to a specific section",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "section_id": {
                            "type": "string",
                            "description": "The ID of the section to add the task to",
                        },
                        "task_id": {
                            "type": "string",
                            "description": "The ID of the task to add",
                        },
                        "insert_before": {
                            "type": "string",
                            "description": "Optional task ID to insert before",
                        },
                        "insert_after": {
                            "type": "string",
                            "description": "Optional task ID to insert after",
                        },
                    },
                    "required": ["section_id", "task_id"],
                },
                outputSchema={
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Array of JSON strings containing the operation results",
                    "examples": [
                        '[{"status":"success","data":{"gid":"12345","name":"Task Name","section":{"gid":"67890","name":"Section Name"}}}]'
                    ],
                },
            ),
            types.Tool(
                name="get_sections",
                description="Get sections in a project, optionally filtered by name",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "project_id": {
                            "type": "string",
                            "description": "The ID of the project to get sections from",
                        },
                        "section_name": {
                            "type": "string",
                            "description": "Optional name to filter sections by",
                        },
                        "limit": {
                            "type": "integer",
                            "description": "Maximum number of sections to return (default: 50)",
                            "minimum": 1,
                            "maximum": 100,
                        },
                    },
                    "required": ["project_id"],
                },
                outputSchema={
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Array of JSON strings containing the operation results",
                    "examples": [
                        '[{"status":"success","data":[{"gid":"12345","name":"Section Name","project":{"gid":"67890","name":"Project Name"}}]}]'
                    ],
                },
            ),
            types.Tool(
                name="delete_section",
                description="Delete a specific section (must be empty and not the last section)",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "section_id": {
                            "type": "string",
                            "description": "The ID of the section to delete",
                        }
                    },
                    "required": ["section_id"],
                },
                outputSchema={
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Array of JSON strings containing the operation results",
                    "examples": ['[{"status":"success","data":{}}]'],
                },
            ),
            types.Tool(
                name="create_tag",
                description="Create a new tag in a workspace or organization",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "workspace_id": {
                            "type": "string",
                            "description": "The ID of the workspace or organization to create the tag in",
                        },
                        "name": {
                            "type": "string",
                            "description": "The name of the tag",
                        },
                        "color": {
                            "type": "string",
                            "description": "Optional color for the tag",
                        },
                        "notes": {
                            "type": "string",
                            "description": "Optional notes for the tag",
                        },
                    },
                    "required": ["workspace_id", "name"],
                },
                outputSchema={
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Array of JSON strings containing the operation results",
                    "examples": [
                        '[{"status":"success","data":{"gid":"12345","name":"New Tag","workspace":{"gid":"67890","name":"My Workspace"}}}]'
                    ],
                },
            ),
            types.Tool(
                name="get_tags",
                description="Get tags in a workspace, optionally filtered by name",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "workspace_id": {
                            "type": "string",
                            "description": "The ID of the workspace to get tags from",
                        },
                        "tag_name": {
                            "type": "string",
                            "description": "Optional name to filter tags by",
                        },
                        "limit": {
                            "type": "integer",
                            "description": "Maximum number of tags to return (default: 50)",
                            "minimum": 1,
                            "maximum": 100,
                        },
                    },
                    "required": ["workspace_id"],
                },
                outputSchema={
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Array of JSON strings containing the operation results",
                    "examples": [
                        '[{"status":"success","data":[{"gid":"12345","name":"Tag Name","workspace":{"gid":"67890","name":"My Workspace"}}}]]'
                    ],
                },
            ),
            types.Tool(
                name="add_tag_to_task",
                description="Add a tag to a task",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "task_id": {
                            "type": "string",
                            "description": "The ID of the task to add the tag to",
                        },
                        "tag_id": {
                            "type": "string",
                            "description": "The ID of the tag to add",
                        },
                    },
                    "required": ["task_id", "tag_id"],
                },
                outputSchema={
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Array of JSON strings containing the operation results",
                    "examples": ['[{"status":"success","data":{}}]'],
                },
            ),
            types.Tool(
                name="remove_tag_from_task",
                description="Remove a tag from a task",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "task_id": {
                            "type": "string",
                            "description": "The ID of the task to remove the tag from",
                        },
                        "tag_id": {
                            "type": "string",
                            "description": "The ID of the tag to remove",
                        },
                    },
                    "required": ["task_id", "tag_id"],
                },
                outputSchema={
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Array of JSON strings containing the operation results",
                    "examples": ['[{"status":"success","data":{}}]'],
                },
            ),
            types.Tool(
                name="create_attachment",
                description="Create an attachment for a task or other object",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "parent_id": {
                            "type": "string",
                            "description": "The ID of the parent object (task, project, etc.)",
                        },
                        "url": {
                            "type": "string",
                            "description": "URL of the external resource to attach",
                        },
                        "name": {
                            "type": "string",
                            "description": "Name for the attachment",
                        },
                        "connect_to_app": {
                            "type": "boolean",
                            "description": "Whether to connect the attachment to an app",
                        },
                    },
                    "required": ["parent_id"],
                },
                outputSchema={
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Array of JSON strings containing the operation results",
                    "examples": [
                        '[{"status":"success","data":{"gid":"12345","name":"New Attachment"}}]'
                    ],
                },
            ),
        ]

    @server.call_tool()
    async def handle_call_tool(name: str, arguments: dict | None) -> list[TextContent]:
        """Handle Asana tool invocation from the MCP system."""
        logger.info(
            f"User {server.user_id} calling tool: {name} with arguments: {arguments}"
        )

        if arguments is None:
            arguments = {}

        asana = await _get_asana_client()

        try:
            if name == "get_me":
                result = asana.get_me()
            elif name == "get_workspaces":
                result = asana.get_workspaces()
            elif name == "get_projects":
                result = asana.get_projects(arguments["workspace_id"])
            elif name == "get_project":
                result = asana.get_project(arguments["project_id"])
            elif name == "create_project":
                result = asana.create_project(
                    workspace_id=arguments["workspace_id"],
                    name=arguments["name"],
                    notes=arguments.get("notes"),
                    color=arguments.get("color"),
                    due_date=arguments.get("due_date"),
                )
            elif name == "get_tasks":
                result = asana.get_tasks(arguments["project_id"])
            elif name == "get_task":
                result = asana.get_task(arguments["task_id"])
            elif name == "create_task":
                result = asana.create_task(
                    name=arguments["name"],
                    project_id=arguments["project_id"],
                    notes=arguments["notes"],
                    assignee=arguments.get("assignee"),
                    due_on=arguments.get("due_on"),
                    completed=arguments["completed"],
                )
            elif name == "update_task":
                result = asana.update_task(
                    task_id=arguments["task_id"],
                    name=arguments.get("name"),
                    notes=arguments.get("notes"),
                )
            elif name == "delete_task":
                result = asana.delete_task(arguments["task_id"])
            elif name == "get_users":
                result = asana.get_users(arguments["workspace_id"])
            elif name == "get_user":
                result = asana.get_user(arguments["user_id"])
            elif name == "duplicate_task":
                result = asana.duplicate_task(arguments["task_id"], arguments["name"])
            elif name == "add_follower_to_task":
                result = asana.add_follower_to_task(
                    arguments["task_id"], arguments["user_id"]
                )
            elif name == "remove_follower_from_task":
                result = asana.remove_follower_from_task(
                    arguments["task_id"], arguments["user_id"]
                )
            elif name == "mark_task_complete":
                result = asana.mark_task_complete(arguments["task_id"])
            elif name == "mark_task_incomplete":
                result = asana.mark_task_incomplete(arguments["task_id"])
            elif name == "add_subtask":
                parent_task_id = arguments.pop("parent_task_id")
                name_arg = arguments.pop("name")
                result = asana.add_subtask(parent_task_id, name_arg, **arguments)
            elif name == "assign_task":
                result = asana.assign_task(arguments["task_id"], arguments["user_id"])
            elif name == "unassign_task":
                result = asana.unassign_task(arguments["task_id"])
            elif name == "add_task_to_project":
                result = asana.add_task_to_project(
                    arguments["task_id"], arguments["project_id"]
                )
            elif name == "remove_task_from_project":
                result = asana.remove_task_from_project(
                    arguments["task_id"], arguments["project_id"]
                )
            elif name == "update_project":
                result = asana.update_project(
                    project_id=arguments["project_id"],
                    name=arguments.get("name"),
                    notes=arguments.get("notes"),
                    color=arguments.get("color"),
                    due_date=arguments.get("due_date"),
                    public=arguments.get("public"),
                    owner=arguments.get("owner"),
                    current_status=arguments.get("current_status"),
                )
            elif name == "create_section":
                result = asana.create_section(
                    arguments["project_id"], arguments["name"]
                )
            elif name == "add_task_to_section":
                result = asana.add_task_to_section(
                    arguments["section_id"],
                    arguments["task_id"],
                    arguments.get("insert_before"),
                    arguments.get("insert_after"),
                )
            elif name == "get_sections":
                result = asana.get_sections(
                    arguments["project_id"],
                    arguments.get("section_name"),
                    arguments.get("limit", 50),
                )
                logger.info(f"Sections: {result}")
            elif name == "delete_section":
                result = asana.delete_section(arguments["section_id"])
            elif name == "create_tag":
                result = asana.create_tag(
                    arguments["workspace_id"],
                    arguments["name"],
                    arguments.get("color"),
                    arguments.get("notes"),
                )
            elif name == "get_tags":
                result = asana.get_tags(
                    arguments["workspace_id"],
                    arguments.get("tag_name"),
                    arguments.get("limit", 50),
                )
            elif name == "add_tag_to_task":
                result = asana.add_tag_to_task(
                    arguments["task_id"], arguments["tag_id"]
                )
            elif name == "remove_tag_from_task":
                result = asana.remove_tag_from_task(
                    arguments["task_id"], arguments["tag_id"]
                )
            elif name == "create_attachment":
                result = asana.create_attachment(
                    parent_id=arguments["parent_id"],
                    url=arguments.get("url"),
                    name=arguments.get("name"),
                    connect_to_app=arguments["connect_to_app"],
                )
            else:
                return [TextContent(type="text", text=f"Unknown tool: {name}")]

            try:
                result_text = json.dumps(
                    {"status": "success", "data": result}, indent=2, default=str
                )
            except:
                result_text = json.dumps(
                    {"status": "success", "data": str(result)}, indent=2
                )

            return [TextContent(type="text", text=result_text)]

        except Exception as e:
            logger.error(f"Error executing tool {name}: {str(e)}")
            return [
                TextContent(
                    type="text",
                    text=json.dumps({"status": "error", "message": str(e)}, indent=2),
                )
            ]

    return server


server = create_server


def get_initialization_options(server_instance: Server) -> InitializationOptions:
    """Define the initialization options for the Asana MCP server."""
    return InitializationOptions(
        server_name="asana-server",
        server_version="1.0.0",
        capabilities=server_instance.get_capabilities(
            notification_options=NotificationOptions(),
            experimental_capabilities={},
        ),
    )


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1].lower() == "auth":
        user_id = "local"
        authenticate_and_save_credentials(user_id, SERVICE_NAME, SCOPES)
    else:
        print("Usage:")
        print("  python main.py auth - Run authentication flow for a user")
        print("Note: To run the server normally, use the guMCP server framework.")
