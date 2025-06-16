"""Member management commands for TracLine."""

import click
import json
from rich.table import Table
from rich.console import Console
from rich.panel import Panel
from tracline.core import Config, TeamService
from tracline.models import MemberRole, MemberPosition


@click.command()
@click.argument('member_id')
@click.argument('name')
@click.option('--role', '-r', 
              type=click.Choice([r.value for r in MemberRole], case_sensitive=False), 
              default=MemberRole.ENGINEER.value, 
              help=f'Member role. Available: {", ".join([r.value for r in MemberRole])}')
@click.option('--position', '-p', 
              type=click.Choice([p.value for p in MemberPosition], case_sensitive=False), 
              default=MemberPosition.MEMBER.value, 
              help=f'Organizational position. Available: {", ".join([p.value for p in MemberPosition])}')
@click.option('--age', type=int, help='Member age')
@click.option('--sex', help='Member sex')
@click.option('--profile', help='Member profile/bio')
@click.option('--leader', '-l', help='Leader/manager ID')
@click.option('--image', help='Profile image path')
@click.pass_context
def add(ctx, member_id, name, role, position, age, sex, profile, leader, image):
    """Add a new team member."""
    config = ctx.obj['config']
    console = ctx.obj['console']
    
    with TeamService(config) as service:
        try:
            member = service.create_member(
                member_id=member_id,
                name=name,
                role=MemberRole(role),
                position=MemberPosition(position),
                age=age,
                sex=sex,
                profile=profile,
                leader_id=leader,
                profile_image_path=image
            )
            
            console.print(f"[green]✓ Member {member_id} created successfully[/green]")
            
            # Show member summary
            table = Table(box=None)
            table.add_column("Field", style="cyan")
            table.add_column("Value", style="white")
            
            table.add_row("ID", member.id)
            table.add_row("Name", member.name)
            table.add_row("Role", member.role)
            table.add_row("Position", member.position)
            if member.age:
                table.add_row("Age", str(member.age))
            if member.sex:
                table.add_row("Sex", member.sex)
            if member.profile:
                table.add_row("Profile", member.profile)
            if member.leader_id:
                table.add_row("Leader", member.leader_id)
            
            console.print(table)
            
        except ValueError as e:
            # Handle invalid enum values
            console.print(f"[red]Error: {e}[/red]")
            console.print("\n[yellow]Available roles:[/yellow]")
            for role in MemberRole:
                console.print(f"  - {role.value}")
            console.print("\n[yellow]Available positions:[/yellow]")
            for pos in MemberPosition:
                console.print(f"  - {pos.value}")
        except Exception as e:
            console.print(f"[red]Error creating member: {e}[/red]")


@click.command()
@click.argument('member_id')
@click.option('--name', help='New name')
@click.option('--role', type=click.Choice([r.value for r in MemberRole]), help='New role')
@click.option('--position', type=click.Choice([p.value for p in MemberPosition]), help='New position')
@click.option('--age', type=int, help='New age')
@click.option('--sex', help='New sex')
@click.option('--profile', help='New profile')
@click.option('--leader', help='New leader ID')
@click.option('--image', help='New profile image path')
@click.pass_context
def update(ctx, member_id, name, role, position, age, sex, profile, leader, image):
    """Update member information."""
    config = ctx.obj['config']
    console = ctx.obj['console']
    
    updates = {}
    if name:
        updates['name'] = name
    if role:
        updates['role'] = MemberRole(role)
    if position:
        updates['position'] = MemberPosition(position)
    if age is not None:
        updates['age'] = age
    if sex:
        updates['sex'] = sex
    if profile:
        updates['profile'] = profile
    if leader:
        updates['leader_id'] = leader
    if image:
        updates['profile_image_path'] = image
    
    if not updates:
        console.print("[yellow]No updates provided[/yellow]")
        return
    
    with TeamService(config) as service:
        member = service.update_member(member_id, **updates)
        if member:
            console.print(f"[green]✓ Member {member_id} updated successfully[/green]")
        else:
            console.print(f"[red]Member {member_id} not found[/red]")


@click.command()
@click.argument('member_id')
@click.option('--force', is_flag=True, help='Force deletion without confirmation')
@click.pass_context
def delete(ctx, member_id, force):
    """Delete a member."""
    config = ctx.obj['config']
    console = ctx.obj['console']
    
    with TeamService(config) as service:
        member = service.get_member(member_id)
        if not member:
            console.print(f"[red]Member {member_id} not found[/red]")
            return
        
        if not force:
            if not click.confirm(f"Are you sure you want to delete member '{member.name}'?"):
                console.print("[yellow]Deletion cancelled[/yellow]")
                return
        
        if service.delete_member(member_id):
            console.print(f"[green]✓ Member {member_id} deleted successfully[/green]")
        else:
            console.print(f"[red]Error deleting member[/red]")


@click.command()
@click.argument('member_id')
@click.option('--details', '-d', is_flag=True, help='Show detailed information')
@click.option('--json', 'as_json', is_flag=True, help='Output as JSON')
@click.pass_context
def show(ctx, member_id, details, as_json):
    """Show member details."""
    config = ctx.obj['config']
    console = ctx.obj['console']
    
    with TeamService(config) as service:
        member = service.get_member(member_id)
        if not member:
            console.print(f"[red]Member {member_id} not found[/red]")
            return
        
        if as_json:
            console.print(json.dumps(member.to_dict(), indent=2))
            return
        
        # Show member details
        panel = Panel(
            f"[bold]{member.name}[/bold]\n"
            f"Role: {member.role}\n"
            f"Position: {member.position}",
            title=f"Member: {member.id}"
        )
        console.print(panel)
        
        if details:
            table = Table(box=None)
            table.add_column("Field", style="cyan")
            table.add_column("Value", style="white")
            
            table.add_row("ID", member.id)
            table.add_row("Name", member.name)
            table.add_row("Role", member.role)
            table.add_row("Position", member.position)
            table.add_row("Age", str(member.age) if member.age else "N/A")
            table.add_row("Sex", member.sex or "N/A")
            table.add_row("Profile", member.profile or "N/A")
            table.add_row("Leader", member.leader_id or "None")
            table.add_row("Image", member.profile_image_path or "None")
            table.add_row("Created", member.created_at.strftime("%Y-%m-%d %H:%M:%S"))
            table.add_row("Updated", member.updated_at.strftime("%Y-%m-%d %H:%M:%S"))
            
            console.print(table)
            
            # Show projects
            projects = service.get_member_projects(member_id)
            if projects:
                console.print("\n[bold]Projects:[/bold]")
                proj_table = Table(box=None)
                proj_table.add_column("ID", style="cyan")
                proj_table.add_column("Name", style="white")
                proj_table.add_column("Status", style="yellow")
                
                for proj in projects:
                    proj_table.add_row(proj.id, proj.name, proj.status)
                
                console.print(proj_table)


@click.command(name='list')
@click.option('--role', type=click.Choice([r.value for r in MemberRole]), help='Filter by role')
@click.option('--position', type=click.Choice([p.value for p in MemberPosition]), help='Filter by position')
@click.option('--leader', help='Filter by leader ID')
@click.option('--json', 'as_json', is_flag=True, help='Output as JSON')
@click.pass_context
def list_members(ctx, role, position, leader, as_json):
    """List all members."""
    config = ctx.obj['config']
    console = ctx.obj['console']
    
    filters = {}
    if role:
        filters['role'] = role
    if position:
        filters['position'] = position
    if leader:
        filters['leader_id'] = leader
    
    with TeamService(config) as service:
        members = service.list_members(filters=filters)
        
        if not members:
            console.print("[yellow]No members found[/yellow]")
            return
        
        if as_json:
            console.print(json.dumps([m.to_dict() for m in members], indent=2))
            return
        
        # Create table
        table = Table(title=f"Members ({len(members)} found)", box=None)
        table.add_column("ID", style="cyan")
        table.add_column("Name", style="white")
        table.add_column("Role", style="yellow")
        table.add_column("Position", style="green")
        table.add_column("Leader", style="magenta")
        table.add_column("Age", style="blue")
        
        for member in members:
            table.add_row(
                member.id,
                member.name,
                member.role,
                member.position,
                member.leader_id or "-",
                str(member.age) if member.age else "-"
            )
        
        console.print(table)


@click.command()
@click.argument('member_id')
@click.argument('new_position', type=click.Choice([p.value for p in MemberPosition]))
@click.pass_context
def change_position(ctx, member_id, new_position):
    """Change a member's organizational position."""
    config = ctx.obj['config']
    console = ctx.obj['console']
    
    with TeamService(config) as service:
        member = service.change_position(member_id, MemberPosition(new_position))
        if member:
            console.print(f"[green]✓ Position changed to {new_position}[/green]")
        else:
            console.print(f"[red]Member {member_id} not found[/red]")


@click.command()
@click.argument('member_id')
@click.argument('new_leader_id', required=False)
@click.pass_context
def change_leader(ctx, member_id, new_leader_id):
    """Change a member's leader/manager."""
    config = ctx.obj['config']
    console = ctx.obj['console']
    
    with TeamService(config) as service:
        member = service.change_leader(member_id, new_leader_id)
        if member:
            if new_leader_id:
                console.print(f"[green]✓ Leader changed to {new_leader_id}[/green]")
            else:
                console.print(f"[green]✓ Leader removed[/green]")
        else:
            console.print(f"[red]Member {member_id} not found[/red]")


@click.command()
@click.argument('leader_id')
@click.option('--json', 'as_json', is_flag=True, help='Output as JSON')
@click.pass_context
def team_structure(ctx, leader_id, as_json):
    """Show team structure under a leader."""
    config = ctx.obj['config']
    console = ctx.obj['console']
    
    from tracline.cli.commands.fixes import safe_get_team_structure
    
    with TeamService(config) as service:
        # Use safe version that handles database-specific issues
        structure = safe_get_team_structure(service, leader_id)
        
        if not structure:
            console.print(f"[red]Leader {leader_id} not found[/red]")
            return
        
        if as_json:
            console.print(json.dumps(structure, indent=2))
            return
        
        def print_hierarchy(node, level=0):
            indent = "  " * level
            name = node.get('name', 'Unknown')
            role = node.get('role', 'Unknown')
            position = node.get('position', 'Unknown')
            console.print(f"{indent}• {name} ({role}) - {position}")
            for report in node.get('direct_reports', []):
                print_hierarchy(report, level + 1)
        
        console.print(f"[bold]Team Structure for {structure.get('name', leader_id)}:[/bold]")
        print_hierarchy(structure)