import os
import subprocess
import sys
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError
from django.conf import settings


class Command(BaseCommand):
    help = 'Build the frontend assets for production'

    def add_arguments(self, parser):
        parser.add_argument(
            '--clean',
            action='store_true',
            help='Clean the dist directory before building',
        )
        parser.add_argument(
            '--install-deps',
            action='store_true',
            help='Install npm dependencies before building',
        )
        parser.add_argument(
            '--watch',
            action='store_true',
            help='Run in watch mode for development',
        )
        parser.add_argument(
            '--app',
            type=str,
            help='Specific app to build frontend for (e.g., django-app-rag)',
        )

    def handle(self, *args, **options):
        # Get the static directory path
        if options.get('app'):
            # Build for specific app
            static_dir = Path(__file__).parent.parent.parent.parent.parent / options['app'] / 'static'
        else:
            # Build for current app (django-app-rag)
            static_dir = Path(__file__).parent.parent.parent.parent / 'static'
        
        if not static_dir.exists():
            raise CommandError(f'Static directory not found: {static_dir}')
        
        # Change to the static directory
        os.chdir(static_dir)
        
        self.stdout.write(
            self.style.SUCCESS(f'Building frontend in: {static_dir}')
        )
        
        # Install dependencies if requested
        if options['install_deps']:
            self.stdout.write('Installing npm dependencies...')
            try:
                subprocess.run(['npm', 'install'], check=True, cwd=static_dir)
                self.stdout.write(
                    self.style.SUCCESS('Dependencies installed successfully')
                )
            except subprocess.CalledProcessError as e:
                raise CommandError(f'Failed to install dependencies: {e}')
            except FileNotFoundError:
                raise CommandError(
                    'npm not found. Please install Node.js and npm first.'
                )
        
        # Clean dist directory if requested
        if options['clean']:
            dist_dir = static_dir / 'dist'
            if dist_dir.exists():
                self.stdout.write('Cleaning dist directory...')
                import shutil
                shutil.rmtree(dist_dir)
                self.stdout.write(
                    self.style.SUCCESS('Dist directory cleaned')
                )
        
        # Build the frontend
        try:
            if options['watch']:
                self.stdout.write('Starting development server in watch mode...')
                subprocess.run(['npm', 'run', 'dev'], cwd=static_dir)
            else:
                self.stdout.write('Building frontend for production...')
                subprocess.run(['npm', 'run', 'build'], check=True, cwd=static_dir)
                self.stdout.write(
                    self.style.SUCCESS('Frontend built successfully!')
                )
                
                # Check if dist directory was created
                dist_dir = static_dir / 'dist'
                if dist_dir.exists():
                    self.stdout.write(
                        f'Build output available in: {dist_dir}'
                    )
                else:
                    self.stdout.write(
                        self.style.WARNING('Warning: dist directory not found after build')
                    )
                    
        except subprocess.CalledProcessError as e:
            raise CommandError(f'Build failed: {e}')
        except FileNotFoundError:
            raise CommandError(
                'npm not found. Please install Node.js and npm first.'
            )
