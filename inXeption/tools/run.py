import asyncio

TRUNCATED_MESSAGE = '<response clipped><NOTE>To save on context only part of this file has been shown to you. You should retry this tool after you have searched inside the file with `grep -n` in order to find the line numbers of what you are looking for.</NOTE>'
MAX_RESPONSE_LEN = 32000


def maybe_truncate(content, truncate_after=MAX_RESPONSE_LEN):
    return (
        content
        if not truncate_after or len(content) <= truncate_after
        else content[:truncate_after] + TRUNCATED_MESSAGE
    )


async def run(
    cmd,
    timeout=180.0,  # seconds
    truncate_after=MAX_RESPONSE_LEN,
):
    process = await asyncio.create_subprocess_shell(
        cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
    )

    try:
        stdout, stderr = await asyncio.wait_for(process.communicate(), timeout=timeout)
        return {
            'exit_code': process.returncode or 0,
            'stdout': maybe_truncate(stdout.decode(), truncate_after=truncate_after),
            'stderr': maybe_truncate(stderr.decode(), truncate_after=truncate_after),
        }
    except asyncio.TimeoutError as exc:
        try:
            process.kill()
        except ProcessLookupError:
            pass
        raise TimeoutError(
            f'Command "{cmd}" timed out after {timeout} seconds'
        ) from exc
