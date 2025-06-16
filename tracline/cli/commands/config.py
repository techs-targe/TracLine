"""Configuration management command for TracLine."""

import click
import yaml
from pathlib import Path
from rich.table import Table
from rich.syntax import Syntax
from tracline.core import Config


@click.command(name='config')
@click.option('--show', is_flag=True, help='Show current configuration')
@click.option('--edit', is_flag=True, help='Edit configuration in default editor')
@click.option('--set', nargs=2, multiple=True, help='Set configuration value (key value)')
@click.option('--get', help='Get specific configuration value')
@click.option('--init', is_flag=True, help='Initialize default configuration file')
@click.pass_context
def config_cmd(ctx, show, edit, set, get, init):
    """Manage TracLine configuration."""
    config = ctx.obj['config']
    console = ctx.obj['console']
    
    if init:
        # Initialize configuration file
        config_path = Path(config.config_path)
        
        if config_path.exists():
            if not click.confirm(f"Configuration already exists at {config_path}. Overwrite?"):
                return
        
        # Create default configuration
        default_config = {
            'database': {
                'type': 'sqlite',
                'path': '~/.tracline/tracline.db'
            },
            'workflow': {
                'custom_states': ['DOING', 'TESTING'],
                'transitions': {
                    'TODO': ['READY'],
                    'READY': ['DOING', 'PENDING', 'CANCELED'],
                    'DOING': ['TESTING', 'PENDING', 'CANCELED'],
                    'TESTING': ['DONE', 'DOING', 'PENDING', 'CANCELED'],
                    'PENDING': ['READY', 'CANCELED']
                }
            },
            'defaults': {
                'assignee': '${TASK_ASSIGNEE}',
                'priority': 3
            }
        }
        
        config_path.parent.mkdir(parents=True, exist_ok=True)
        with open(config_path, 'w') as f:
            yaml.dump(default_config, f, default_flow_style=False)
        
        console.print(f"[green]✓ Configuration initialized at {config_path}[/green]")
        return
    
    if show:
        # Show current configuration
        console.print("[bold]Current Configuration:[/bold]\n")
        
        # Load raw config for display
        config_data = config.config.dict()
        yaml_str = yaml.dump(config_data, default_flow_style=False)
        
        syntax = Syntax(yaml_str, "yaml", theme="monokai")
        console.print(syntax)
        
        console.print(f"\n[dim]Configuration file: {config.config_path}[/dim]")
        return
    
    if edit:
        # Edit configuration in default editor
        import os
        import subprocess
        
        editor = os.environ.get('EDITOR', 'vi')
        config_path = Path(config.config_path)
        
        if not config_path.exists():
            console.print("[red]Configuration file not found. Run --init first.[/red]")
            return
        
        try:
            subprocess.call([editor, str(config_path)])
            console.print("[green]✓ Configuration edited[/green]")
        except Exception as e:
            console.print(f"[red]Error editing configuration: {e}[/red]")
        return
    
    if set:
        # Set configuration values
        config_data = config.config.dict()
        
        for key, value in set:
            # Navigate nested keys
            keys = key.split('.')
            current = config_data
            
            for k in keys[:-1]:
                if k not in current:
                    current[k] = {}
                current = current[k]
            
            # Set the value
            current[keys[-1]] = value
            console.print(f"[green]✓ Set {key} = {value}[/green]")
        
        # Save configuration
        config.config = type(config.config)(**config_data)
        config.save_config()
        return
    
    if get:
        # Get specific configuration value
        keys = get.split('.')
        current = config.config.dict()
        
        try:
            for key in keys:
                current = current[key]
            console.print(f"{get}: {current}")
        except KeyError:
            console.print(f"[red]Configuration key not found: {get}[/red]")
        return
    
    # Show available options if no action specified
    console.print("[bold]Configuration Management:[/bold]\n")
    console.print("Options:")
    console.print("  --show     Show current configuration")
    console.print("  --edit     Edit configuration in default editor")
    console.print("  --set      Set configuration value")
    console.print("  --get      Get configuration value")
    console.print("  --init     Initialize default configuration\n")
    console.print("Examples:")
    console.print("  tracline config --show")
    console.print("  tracline config --set database.type postgresql")
    console.print("  tracline config --get defaults.assignee")