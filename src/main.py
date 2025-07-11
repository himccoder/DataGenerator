"""
Main application entry point for calendar data generation.

This module provides the Command Line Interface (CLI) for the application.
It uses the Click framework to create a professional, user-friendly interface.

Architecture Pattern: CLI Controller / Command Pattern
- Each command is a separate function
- Shared context object holds common components
- Clean separation between CLI and business logic
- Professional user experience with progress bars, colors, etc.

CLI Design Principles:
- Clear, descriptive command names
- Helpful options and flags
- Good error messages
- Progress feedback for long operations
- Consistent output formatting
"""

import click
from datetime import datetime
from pathlib import Path

from .config_loader import ConfigLoader
from .database import RedisManager
from .data_generator import DataGenerator


@click.group()
@click.pass_context
def cli(ctx):
    """Calendar Data Generation Tool
    
    Generate realistic calendar users and events using LLMs (OpenAI GPT & DeepSeek).
    Data is stored in Redis and exported to JSON files.
    """
    ctx.ensure_object(dict)
    
    # Initialize components
    try:
        config_loader = ConfigLoader()
        redis_manager = RedisManager(config_loader.get_database_config())
        data_generator = DataGenerator(config_loader, redis_manager)
        
        ctx.obj['config'] = config_loader
        ctx.obj['redis'] = redis_manager
        ctx.obj['generator'] = data_generator
        
    except Exception as e:
        click.echo(f" Initialization failed: {e}", err=True)
        ctx.exit(1)


@cli.command()
@click.option('--users', '-u', default=None, type=int, help='Number of users to generate')
@click.option('--provider', '-p', type=click.Choice(['openai', 'deepseek']), help='LLM provider to use')
@click.option('--dry-run', is_flag=True, help='Show what would be generated without actually doing it')
@click.pass_context
def generate(ctx, users, provider, dry_run):
    """Generate calendar data (users and events)."""
    generator = ctx.obj['generator']
    config = ctx.obj['config']
    
    if users is None:
        users = config.get_generation_config().get('users', {}).get('count', 50)
    
    if dry_run:
        click.echo(f"🔍 DRY RUN: Would generate {users} users with events using {provider or 'any available'} provider")
        return
    
    click.echo(f" Starting data generation...")
    click.echo(f" Users to generate: {users}")
    click.echo(f" Provider: {provider or 'auto-select'}")
    
    try:
        with click.progressbar(length=100, label='Generating data') as bar:
            # This is a simplified progress bar - in a real implementation,
            # you'd want to update it during generation
            bar.update(50)
            
            results = generator.generate_and_save(users, provider)
            
            bar.update(50)
        
        # Display results
        click.echo("\n Generation completed successfully!")
        click.echo(f" Users generated: {results['users_generated']}")
        click.echo(f" Events generated: {results['events_generated']}")
        click.echo(f" Duration: {results['duration_seconds']:.2f} seconds")
        click.echo(f" API calls made: {results['api_calls']}")
        
        if results['failed_generations'] > 0:
            click.echo(f" Failed generations: {results['failed_generations']}")
        
        click.echo("\n Exported files:")
        for file_type, file_path in results['exported_files'].items():
            click.echo(f"  - {file_type}: {file_path}")
        
    except Exception as e:
        click.echo(f" Generation failed: {e}", err=True)
        ctx.exit(1)


@cli.command()
@click.pass_context
def stats(ctx):
    """Show database and generation statistics."""
    redis_manager = ctx.obj['redis']
    
    try:
        stats = redis_manager.get_stats()
        
        click.echo(" Database Statistics")
        click.echo("=" * 30)
        click.echo(f"Users in database: {stats['users_count']}")
        click.echo(f"Events in database: {stats['events_count']}")
        click.echo(f"Memory usage: {stats['memory_usage']}")
        click.echo(f"Connection status: {stats['connection_status']}")
        
    except Exception as e:
        click.echo(f" Failed to get statistics: {e}", err=True)


@cli.command()
@click.confirmation_option(prompt='Are you sure you want to clear all data?')
@click.pass_context
def clear(ctx):
    """Clear all data from Redis database."""
    redis_manager = ctx.obj['redis']
    
    try:
        success = redis_manager.clear_all_data()
        if success:
            click.echo(" All data cleared successfully")
        else:
            click.echo(" Failed to clear data", err=True)
    except Exception as e:
        click.echo(f" Clear operation failed: {e}", err=True)


@cli.command()
@click.option('--format', '-f', type=click.Choice(['json', 'csv']), default='json', help='Export format')
@click.pass_context
def export(ctx, format):
    """Export existing data from Redis to files."""
    redis_manager = ctx.obj['redis']
    
    try:
        users = redis_manager.get_all_users()
        events = redis_manager.get_all_events()
        
        if not users and not events:
            click.echo(" No data found in database to export")
            return
        
        # Create export directory
        output_dir = Path("data/exported")
        output_dir.mkdir(parents=True, exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        if format == 'json':
            import json
            
            # Export users
            users_file = output_dir / f"users_export_{timestamp}.json"
            with open(users_file, 'w', encoding='utf-8') as f:
                json.dump([user.dict() for user in users], f, indent=2, default=str)
            
            # Export events
            events_file = output_dir / f"events_export_{timestamp}.json"
            with open(events_file, 'w', encoding='utf-8') as f:
                json.dump([event.dict() for event in events], f, indent=2, default=str)
            
            click.echo(f" Exported {len(users)} users and {len(events)} events to JSON files:")
            click.echo(f"  - Users: {users_file}")
            click.echo(f"  - Events: {events_file}")
        
        elif format == 'csv':
            import pandas as pd
            
            # Export users to CSV
            if users:
                users_df = pd.DataFrame([user.dict() for user in users])
                users_csv = output_dir / f"users_export_{timestamp}.csv"
                users_df.to_csv(users_csv, index=False)
                click.echo(f"  - Users CSV: {users_csv}")
            
            # Export events to CSV
            if events:
                events_df = pd.DataFrame([event.dict() for event in events])
                events_csv = output_dir / f"events_export_{timestamp}.csv"
                events_df.to_csv(events_csv, index=False)
                click.echo(f"  - Events CSV: {events_csv}")
                
            click.echo(f" Exported {len(users)} users and {len(events)} events to CSV files")
        
    except Exception as e:
        click.echo(f" Export failed: {e}", err=True)


@cli.command()
@click.pass_context
def test_connection(ctx):
    """Test connections to LLM APIs and Redis."""
    config = ctx.obj['config']
    redis_manager = ctx.obj['redis']
    
    click.echo("🔧 Testing connections...")
    
    # Test Redis
    try:
        redis_manager.client.ping()
        click.echo(" Redis connection: OK")
    except Exception as e:
        click.echo(f" Redis connection: FAILED - {e}")
    
    # Test OpenAI
    openai_config = config.get_api_config('openai')
    if openai_config.get('api_key'):
        try:
            from .llm_clients import OpenAIClient
            client = OpenAIClient(openai_config)
            # Simple test call
            response = client.generate_text("Say 'Hello from OpenAI'")
            if response:
                click.echo(" OpenAI API: OK")
            else:
                click.echo(" OpenAI API: Empty response")
        except Exception as e:
            click.echo(f" OpenAI API: FAILED - {e}")
    else:
        click.echo(" OpenAI API: No API key configured")
    
    # Test DeepSeek
    deepseek_config = config.get_api_config('deepseek')
    if deepseek_config.get('api_key'):
        try:
            from .llm_clients import DeepSeekClient
            client = DeepSeekClient(deepseek_config)
            response = client.generate_text("Say 'Hello from DeepSeek'")
            if response:
                click.echo(" DeepSeek API: OK")
            else:
                click.echo(" DeepSeek API: Empty response")
        except Exception as e:
            click.echo(f" DeepSeek API: FAILED - {e}")
    else:
        click.echo(" DeepSeek API: No API key configured")


def main():
    """Entry point for the application."""
    cli()


if __name__ == '__main__':
    main() 