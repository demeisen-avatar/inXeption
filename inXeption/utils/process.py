'''
Process monitoring utilities for tracking and identifying new processes.
'''

import logging
from typing import Any, Dict

import psutil

# Initialize logger for this module
logger = logging.getLogger(__name__)


async def get_process_info() -> Dict[int, Dict[str, Any]]:
    '''
    Get information about all running processes using psutil.

    Returns:
        Dict mapping PIDs to process information dictionaries.
    '''
    result = {}

    for proc in psutil.process_iter(['pid', 'ppid', 'name', 'cmdline', 'username']):
        try:
            # Get process info as a dictionary
            proc_info = proc.info
            pid = proc_info['pid']

            # Store relevant information
            result[pid] = {
                'ppid': proc_info['ppid'],
                'name': proc_info['name'],
                'cmd': ' '.join(proc_info['cmdline']),
                'username': proc_info['username'],
            }
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            # Skip processes that can't be accessed or have terminated
            pass

    return result


def find_new_processes(
    before: Dict[int, Dict[str, Any]], after: Dict[int, Dict[str, Any]]
):
    '''
    Find processes that exist in 'after' but not in 'before'.

    Args:
        before: Process dictionary before an operation
        after: Process dictionary after an operation

    Returns:
        Dict of new processes with their information
    '''
    new_pids = set(after.keys()) - set(before.keys())
    new_processes = {}

    for pid in new_pids:
        new_processes[pid] = after[pid]
        new_processes[pid]['is_bash'] = 'bash' in after[pid]['name'] + after[pid]['cmd']

    return new_processes


def log_process_changes(
    logger,
    before: Dict[int, Dict[str, Any]],
    after: Dict[int, Dict[str, Any]],
    run_index: int = 0,
):
    '''
    Log any new processes created between before and after snapshots.

    Args:
        logger: Logger to use for output
        before: Process dictionary before an operation
        after: Process dictionary after an operation
        run_index: Optional run index for logging context
    '''
    new_processes = find_new_processes(before, after)

    if new_processes:
        logger.warning(
            f'Found {len(new_processes)} new processes:', extra={'run_index': run_index}
        )

        # Log bash processes first and more prominently
        bash_procs = {
            pid: info for pid, info in new_processes.items() if info['is_bash']
        }
        if bash_procs:
            logger.warning(
                f'!!! FOUND {len(bash_procs)} NEW BASH PROCESSES !!!',
                extra={'run_index': run_index},
            )
            for pid, info in bash_procs.items():
                logger.warning(
                    f'New bash process: PID={pid}, PPID={info["ppid"]}, '
                    f'CMD={info["cmd"]}, User={info["username"]}',
                    extra={'run_index': run_index},
                )

        # Log other processes
        other_procs = {
            pid: info for pid, info in new_processes.items() if not info['is_bash']
        }
        if other_procs:
            logger.info(
                f'Other new processes: {len(other_procs)}',
                extra={'run_index': run_index},
            )
            for pid, info in other_procs.items():
                logger.info(
                    f'New process: PID={pid}, PPID={info["ppid"]}, '
                    f'Name={info["name"]}, User={info["username"]}',
                    extra={'run_index': run_index},
                )
    else:
        logger.info('No new processes detected', extra={'run_index': run_index})
