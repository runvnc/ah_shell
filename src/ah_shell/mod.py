import os
import subprocess
import fnmatch
from lib.providers.commands import command
from gitignore_parser import parse_gitignore
from collections import OrderedDict

DEFAULT_EXCLUDE = ['.git', 'node_modules', 'dist', 'build', 'coverage', '__pycache__', '.ipynb_checkpoints']

@command()
async def execute_command(cmd="", context=None):
    """Execute a system command and return the output.

    Example:
    
    { "execute_command": { "cmd": START_RAW
python -c "
import random
numbers = [random.randint(1, 100) for _ in range(10)]
print('Random numbers:', numbers)
print('Sum:', sum(numbers))
"
END_RAW
} }

    Note: if you need to see the result of your command, 
    DO NOT end your command list with task_complete() or similar --
    you will not receive the results until after the user replies.

    """
    #if 'current_dir' in context.data:
    #    os.makedirs(context.data['current_dir'], exist_ok=True)
    #    cmd = f'cd {context.data["current_dir"]} && {cmd}'
    try:
        result = subprocess.run(cmd, shell=True, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        output = result.stdout.decode('utf-8')
        error = result.stderr.decode('utf-8')
        if error:
            return f"Command executed with stderr output:\n{error}\nStdout:\n{output}"
        return output
    except subprocess.CalledProcessError as e:
        return f"Command '{cmd}' failed with error code {e.returncode}:\nStderr:\n{e.stderr.decode('utf-8')}\nStdout:\n{e.stdout.decode('utf-8')}"

@command()
async def mkdir(absolute_path="", context=None):
    """Create a new directory.
    Example:
    { "mkdir": { "absolute_path": "/some/new_folder" } }
    """
    try:
        os.makedirs(absolute_path, exist_ok=True)
        return f"Directory '{absolute_path}' created successfully."
    except Exception as e:
        return f"Failed to create directory '{absolute_path}': {e}"

def should_exclude(path, matches):
    return any(fnmatch.fnmatch(path, pattern) for pattern in DEFAULT_EXCLUDE) or matches(path)

@command()
async def tree(directory='', context=None):
    """List directory structure excluding patterns from .gitignore and default exclusions.
    Example:
    { "tree": { "directory": "" } }
    """
    if 'current_dir' in context.data:
        directory = os.path.join(context.data['current_dir'], directory)
    gitignore_path = os.path.join(directory, '.gitignore')
    if os.path.exists(gitignore_path):
        matches = parse_gitignore(gitignore_path)
    else:
        matches = lambda path: False

    def list_dir(dir_path):
        tree_structure = []
        for root, dirs, files in os.walk(dir_path):
            dirs[:] = [d for d in dirs if not should_exclude(os.path.join(root, d), matches)]
            files = [f for f in files if not should_exclude(os.path.join(root, f), matches)]
            node = OrderedDict()
            node['root'] = root
            node['dirs'] = dirs
            node['files'] = files
            tree_structure.append(node)
        return tree_structure

    tree_structure = list_dir(directory)
    return tree_structure

class TestContext:
    def __init__(self, data):
        self.data = data

if __name__ == '__main__':
    import asyncio
    from pprint import pprint
    async def main():
        cmd = 'ls -la'
        context = TestContext({'current_dir': '/files/ah'})

        result = await execute_command(cmd, context=context)
        print(result)
        directory = 'new_folder'
        result = await mkdir(directory, context=context)
        print(result)
        directory = ''
        result = await tree(directory, context=context)
        pprint(result)
    asyncio.run(main())

@command()
async def run_python(text="", context=None):
    """Execute Python code by writing it to a temporary file and running it.
    The code will be executed with the current process working directory,
    but the temporary file will be created in /tmp/.
    
    Example:
    { "run_python": { "text": "print('Hello World!')\nfor i in range(3):\n    print(f'Count: {i}')" } }
    
    Note: if you need to see the result of your code execution,
    DO NOT end your command list with task_complete() or similar --
    you will not receive the results until after the user replies.
    """
    import tempfile
    import os
    
    try:
        # Create a temporary Python file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', dir='/tmp', delete=False) as temp_file:
            temp_file.write(text)
            temp_filename = temp_file.name
        
        # Execute the Python file
        result = subprocess.run(['python', temp_filename], 
                              capture_output=True, text=True, check=True)
        
        # Clean up the temporary file
        os.unlink(temp_filename)
        
        output = result.stdout
        error = result.stderr
        
        if error:
            return f"Python code executed with stderr output:\n{error}\nStdout:\n{output}"
        return output
        
    except subprocess.CalledProcessError as e:
        # Clean up the temporary file if it exists
        if 'temp_filename' in locals() and os.path.exists(temp_filename):
            os.unlink(temp_filename)
        return f"Python code execution failed with error code {e.returncode}:\nStderr:\n{e.stderr}\nStdout:\n{e.stdout}"
    except Exception as e:
        # Clean up the temporary file if it exists
        if 'temp_filename' in locals() and os.path.exists(temp_filename):
            os.unlink(temp_filename)
        return f"Failed to execute Python code: {e}"
