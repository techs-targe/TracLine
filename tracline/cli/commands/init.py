"""Init command for TracLine."""

import click
import time
from pathlib import Path
from tracline.core import Config
from tracline.db import DatabaseFactory


@click.command()
@click.option(
    '--sample-data',
    is_flag=True,
    help='Initialize with sample data'
)
@click.option(
    '--force',
    is_flag=True,
    help='Force reinitialization'
)
@click.pass_context
def init(ctx, sample_data, force):
    """Initialize TracLine database and configuration."""
    config = ctx.obj['config']
    console = ctx.obj['console']
    
    # Create database instance
    db = DatabaseFactory.create(config.get_database_config())
    
    # Initialize schema with enhanced safety
    try:
        db.connect()
        
        # Initialize database schema
        try:
            db.initialize_schema()
            console.print("[green]✓ Database initialized successfully[/green]")
        except Exception as e:
            console.print(f"[yellow]Database initialization warning: {e}[/yellow]")
        
        # Only proceed with data creation if sample_data is requested
        if sample_data:
            console.print("\n[bold]Creating sample data...[/bold]")
            
            from tracline.core import TaskService
            from tracline.core.team_service import TeamService
            from tracline.models import MemberRole, MemberPosition
            import os
            
            service = TaskService(config, db)
            team_service = TeamService(config, db)
            
            # Generate unique timestamp for IDs to avoid conflicts
            timestamp = int(time.time())
            
            # Create sample project
            try:
                # Check if sample project already exists
                existing_project = team_service.get_project("SAMPLE-PROJECT")
                if existing_project:
                    console.print(f"[yellow]Sample project already exists, skipping creation[/yellow]")
                    sample_project = existing_project
                else:
                    sample_project = team_service.create_project(
                        project_id="SAMPLE-PROJECT",
                        name="TracLine Sample Project",
                        description="Example project demonstrating TracLine features"
                    )
                    console.print(f"[green]✓ Created sample project: {sample_project.name}[/green]")
                
                # Set sample project as current
                config.set_current_project("SAMPLE-PROJECT")
                
                # Create sample files directory
                sample_dir = Path.home() / "TracLine" / "SampleData"
                sample_dir.mkdir(parents=True, exist_ok=True)
                console.print(f"[green]✓ Created sample data directory: {sample_dir}[/green]")
                
            except Exception as e:
                console.print(f"[red]Error creating sample project: {e}[/red]")
                return
            
            # Create sample members with hierarchy
            sample_members = [
                # (id, name, role, position, leader_id)
                ("alice-manager", "Alice Manager", MemberRole.PM, MemberPosition.LEADER, None),
                ("bob-lead", "Bob Lead", MemberRole.TL, MemberPosition.SUB_LEADER, "alice-manager"),
                ("john-doe", "John Doe", MemberRole.ENGINEER, MemberPosition.MEMBER, "bob-lead"),
                ("jane-smith", "Jane Smith", MemberRole.DESIGNER, MemberPosition.MEMBER, "alice-manager"),
                ("charlie-dev", "Charlie Developer", MemberRole.ENGINEER, MemberPosition.MEMBER, "john-doe"),
                ("diana-test", "Diana Tester", MemberRole.TESTER, MemberPosition.MEMBER, "bob-lead"),
            ]
            
            members_created = 0
            member_map = {}  # Track created members for hierarchy
            
            for member_data in sample_members:
                member_id, name, role, position, leader_id = member_data
                
                try:
                    # Check if member already exists
                    existing_member = team_service.get_member(member_id)
                    if existing_member:
                        console.print(f"[dim]Member {member_id} already exists, skipping[/dim]")
                        member_map[member_id] = existing_member
                    else:
                        member = team_service.create_member(
                            member_id=member_id,
                            name=name,
                            role=role,
                            position=position,
                            leader_id=leader_id
                        )
                        member_map[member_id] = member
                        members_created += 1
                        
                        # Add member to project
                        try:
                            team_service.add_project_member("SAMPLE-PROJECT", member_id)
                        except Exception as e:
                            console.print(f"[yellow]Warning: Could not add {member_id} to project: {e}[/yellow]")
                except Exception as member_error:
                    console.print(f"[yellow]Error creating member {member_id}: {member_error}[/yellow]")
            
            if members_created > 0:
                console.print(f"[green]✓ Created {members_created} sample members[/green]")
            
            # Create sample files
            sample_files = [
                ("requirements.md", "# Project Requirements\n\n## Authentication\n- JWT-based authentication\n- Role-based access control\n\n## User Management\n- User profiles\n- Team hierarchy"),
                ("design/ui_mockups.md", "# UI Design Mockups\n\n## Login Screen\n- Clean, modern interface\n- Remember me option\n\n## Dashboard\n- Task overview\n- Team member status"),
                ("src/auth.py", "# Authentication Module\n\ndef authenticate(username, password):\n    \"\"\"Authenticate user with JWT\"\"\"\n    pass\n\ndef generate_token(user):\n    \"\"\"Generate JWT token\"\"\"\n    pass"),
                ("tests/test_auth.py", "# Authentication Tests\n\nimport pytest\n\ndef test_login():\n    \"\"\"Test user login\"\"\"\n    assert True\n\ndef test_token_generation():\n    \"\"\"Test JWT token generation\"\"\"\n    assert True"),
                ("docs/api_spec.yaml", "openapi: 3.0.0\ninfo:\n  title: TracLine API\n  version: 1.0.0\npaths:\n  /login:\n    post:\n      summary: User login\n      responses:\n        200:\n          description: Success"),
            ]
            
            files_created = 0
            for file_path, content in sample_files:
                try:
                    full_path = sample_dir / file_path
                    full_path.parent.mkdir(parents=True, exist_ok=True)
                    full_path.write_text(content)
                    files_created += 1
                except Exception as e:
                    console.print(f"[yellow]Error creating file {file_path}: {e}[/yellow]")
            
            if files_created > 0:
                console.print(f"[green]✓ Created {files_created} sample files[/green]")
            
            # Create sample tasks with file associations
            sample_tasks = [
                ("REQ-001", "User Authentication Requirements", "Define and document authentication requirements", "alice-manager", "TODO", [("requirements.md", "Requirements document")]),
                ("DES-001", "UI/UX Design", "Design user interface mockups", "jane-smith", "DOING", [("design/ui_mockups.md", "UI mockup designs")]),
                ("DEV-001", "Implement Authentication", "Implement JWT-based authentication system", "john-doe", "DOING", [("src/auth.py", "Authentication implementation"), ("docs/api_spec.yaml", "API specification")]),
                ("DEV-002", "Authentication Unit Tests", "Write unit tests for authentication", "charlie-dev", "TODO", [("tests/test_auth.py", "Test implementation")]),
                ("QA-001", "Test Authentication Flow", "End-to-end testing of authentication", "diana-test", "READY", []),
                ("DOC-001", "API Documentation", "Document authentication API endpoints", "bob-lead", "TODO", [("docs/api_spec.yaml", "API documentation")]),
            ]
            
            tasks_created = 0
            task_file_associations = {}
            
            for task_data in sample_tasks:
                task_id, title, desc, assignee, status = task_data[:5]
                file_associations = task_data[5] if len(task_data) > 5 else []
                
                try:
                    # Check if task already exists
                    existing_task = service.get_task(task_id)
                    if existing_task:
                        console.print(f"[dim]Task {task_id} already exists, skipping[/dim]")
                        # Still store file associations for existing tasks
                        if file_associations:
                            task_file_associations[task_id] = file_associations
                    else:
                        # Create task
                        task = service.create_task(
                            task_id=task_id,
                            title=title,
                            description=desc,
                            assignee=assignee,
                            project_id="SAMPLE-PROJECT"
                        )
                        
                        # Update status if not TODO
                        if status != "TODO":
                            try:
                                service.update_task(task_id, status=status)
                            except Exception as e:
                                console.print(f"[yellow]Warning: Could not update task {task_id} status: {e}[/yellow]")
                        
                        tasks_created += 1
                        
                        # Store file associations for later
                        if file_associations:
                            task_file_associations[task_id] = file_associations
                        
                except Exception as task_error:
                    console.print(f"[yellow]Error creating task {task_id}: {task_error}[/yellow]")
            
            if tasks_created > 0:
                console.print(f"[green]✓ Created {tasks_created} sample tasks[/green]")
            
            # Create file associations
            associations_created = 0
            for task_id, associations in task_file_associations.items():
                for file_path, description in associations:
                    try:
                        full_file_path = str(sample_dir / file_path)
                        
                        # Check if file association already exists
                        try:
                            existing_associations = db.get_file_associations(task_id)
                            association_exists = any(assoc.file_path == full_file_path for assoc in existing_associations)
                            if association_exists:
                                console.print(f"[dim]File association {file_path} -> {task_id} already exists, skipping[/dim]")
                                continue
                        except:
                            pass  # If we can't check, proceed with creation
                        
                        # Create file association using proper abstraction
                        from tracline.models import FileAssociation
                        file_assoc = FileAssociation(
                            task_id=task_id,
                            file_path=full_file_path,
                            file_type=Path(file_path).suffix[1:] if Path(file_path).suffix else 'txt',
                            description=description
                        )
                        db.add_file_association(file_assoc)
                        associations_created += 1
                    except Exception as e:
                        console.print(f"[yellow]Error creating file association: {e}[/yellow]")
            
            if associations_created > 0:
                console.print(f"[green]✓ Created {associations_created} file associations[/green]")
            
            # Create task relationships
            from tracline.models.relationship import RelationshipType
            
            relationships = [
                ("REQ-001", "DES-001", RelationshipType.BLOCKS),  # Requirements block design
                ("DES-001", "DEV-001", RelationshipType.BLOCKS),  # Design blocks development
                ("DEV-001", "DEV-002", RelationshipType.RELATED),  # Dev relates to tests
                ("DEV-002", "QA-001", RelationshipType.BLOCKS),  # Tests block QA
                ("REQ-001", "DOC-001", RelationshipType.RELATED),  # Requirements relate to docs
            ]
            
            relationships_created = 0
            for parent_id, child_id, rel_type in relationships:
                try:
                    # Multiple-layer protection against UNIQUE constraint failures
                    relationship_exists = False
                    
                    # Method 1: Check using database query
                    try:
                        rel_type_value = rel_type.value if hasattr(rel_type, 'value') else str(rel_type)
                        query = "SELECT COUNT(*) FROM task_relationships WHERE parent_id = ? AND child_id = ? AND relationship_type = ?"
                        cursor = db.execute_query(query, [parent_id, child_id, rel_type_value])
                        count = cursor.fetchone()[0]
                        
                        if count > 0:
                            relationship_exists = True
                            console.print(f"[dim]Relationship {parent_id}->{child_id} already exists, skipping[/dim]")
                    except Exception as check_error:
                        console.print(f"[dim]Database check failed, trying alternative method: {check_error}[/dim]")
                        
                        # Method 2: Try using service method as fallback
                        try:
                            existing_relationships = service.get_task_relationships(parent_id)
                            for rel in existing_relationships:
                                if (rel.child_id == child_id and 
                                    str(rel.relationship_type) == str(rel_type_value)):
                                    relationship_exists = True
                                    console.print(f"[dim]Relationship {parent_id}->{child_id} found via service, skipping[/dim]")
                                    break
                        except Exception:
                            pass  # Continue with creation attempt
                    
                    if relationship_exists:
                        continue
                    
                    # Attempt to create relationship
                    service.link_tasks(parent_id, child_id, relationship_type=rel_type)
                    relationships_created += 1
                    console.print(f"[green]✓ Created relationship {parent_id}->{child_id}[/green]")
                    
                except Exception as link_error:
                    error_msg = str(link_error)
                    if any(phrase in error_msg.lower() for phrase in ["unique constraint", "duplicate", "already exists"]):
                        console.print(f"[dim]Relationship {parent_id}->{child_id} already exists (detected by error), skipping[/dim]")
                    else:
                        console.print(f"[yellow]Error creating relationship {parent_id}->{child_id}: {link_error}[/yellow]")
            
            if relationships_created > 0:
                console.print(f"[green]✓ Created {relationships_created} task relationships[/green]")
                
            # Summary
            console.print("\n[bold green]Sample data creation complete![/bold green]")
            console.print(f"  Project: SAMPLE-PROJECT")
            console.print(f"  Members: {members_created}")
            console.print(f"  Tasks: {tasks_created}")
            console.print(f"  Files: {files_created}")
            console.print(f"  File associations: {associations_created}")
            console.print(f"  Relationships: {relationships_created}")
            console.print(f"\nSample files location: {sample_dir}")
        
        else:
            # Clean installation - no data
            console.print("[dim]Clean installation - no sample data created[/dim]")
        
        # Save configuration
        try:
            config_path = Path(config.config_path) if hasattr(config, 'config_path') else None
            if config_path and not config_path.exists() and hasattr(config, 'save_config'):
                config.save_config()
                console.print(f"[green]✓ Configuration saved to {config_path}[/green]")
        except Exception as config_error:
            console.print(f"[yellow]Error saving configuration: {config_error}[/yellow]")
        
        console.print("\n[bold]TracLine v2 initialized![/bold]")
        console.print("Run 'tracline next' to get your first task.")
        
    except Exception as e:
        console.print(f"[red]Error initializing database: {e}[/red]")
    finally:
        try:
            db.disconnect()
        except Exception:
            pass