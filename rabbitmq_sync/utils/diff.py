import dataclasses
from typing import Literal
import myers
from myers import KEEP, INSERT, REMOVE


@dataclasses.dataclass
class LineBlock:
    lines: list[str] = dataclasses.field(default_factory=list)

    def append(self, line: str):
        self.lines.append(line)

    def render(self):
        return "\n".join(self.lines)


@dataclasses.dataclass
class ConflictBlock(LineBlock):
    diff_lines: list[str] = dataclasses.field(default_factory=list)
    insert_diff: bool = False
    diff_postfix: str = None
    auto_resolve: bool = False
    resolve_for_this: bool = True

    def append(self, line: str):
        (self.diff_lines if self.insert_diff else self.lines).append(line)

    @staticmethod
    def join(collection):
        return "\n".join(collection)

    def render(self):
        has_conflict = any(self.lines) and any(self.diff_lines)
        if self.auto_resolve and not has_conflict:
            return self.render_resolve()
        return self.render_diff()

    def render_diff(self):
        result = [self.diff_line_for('<')]
        if self.lines:
            result.append(self.join(self.lines))
        result.append('=======')
        if self.diff_lines:
            result.append(self.join(self.diff_lines))
        result.append(self.diff_line_for('>'))

        return "\n".join(result)

    def diff_line_for(self, symbol: str):
        return symbol * 7 + (f' {self.diff_postfix}'.rstrip())

    def render_resolve(self):
        if self.resolve_for_this:
            return self.join(self.lines)
        return self.join(self.diff_lines)


def git_diff_resolve(a: str | list, b: str | list, auto_resolve: Literal['a', 'b'] | str = None, diff_postfix=None) -> str:
    if isinstance(a, str):
        a = a.split('\n')
    if isinstance(b, str):
        b = b.split('\n')

    do_resolve = auto_resolve is not None
    resolve_a = auto_resolve == 'a'

    diffs = myers.diff(a, b)

    blocks = []

    block_state = 0

    def create_conflict_block(insert_diff: bool):
        return ConflictBlock(
            auto_resolve=do_resolve,
            resolve_for_this=resolve_a,
            insert_diff=insert_diff,
            diff_postfix=diff_postfix)

    def last_block():
        return blocks[-1]

    def render_blocks():
        result = []
        for block in blocks:
            result.append(block.render())
            if type(block) == LineBlock:
                result.append('\n')

        return ''.join(result)

    '''
    States:
    0 - no diff block
    1 - A part
    2 - B part
    
    0
    <<<<<<<
    1
    =======
    2
    >>>>>>>
    0
    '''
    block_prev_action = KEEP

    for action, line in diffs:

        if action == KEEP:
            block_state = 0
            blocks.append(LineBlock())
        elif block_state == 0 and action == REMOVE:
            block_state = 1
            blocks.append(create_conflict_block(insert_diff=False))
        elif block_state == 0 and action == INSERT:
            block_state = 2
            blocks.append(create_conflict_block(insert_diff=True))
        elif block_state == 1 and action != KEEP and action != block_prev_action:
            last_block().insert_diff = True
            block_state = 2
        elif block_state == 1 and action == KEEP:
            block_state = 0
        elif block_state == 2 and (action == KEEP or action != block_prev_action):
            block_state = 0

        print(action, line, block_state)

        last_block().append(line)

        block_prev_action = action

    return render_blocks()


def git_diff(a: str | list, b: str | list, a_name='', b_name='') -> str:
    if isinstance(a, str):
        a = a.split('\n')
    if isinstance(b, str):
        b = b.split('\n')

    a.append('')
    b.append('')

    diffs = myers.diff(a, b)

    lines = []

    block_start = '<' * 7 + (f' {a_name}'.rstrip())
    block_sep = '=' * 7
    block_end = '>' * 7 + (f' {b_name}'.rstrip())

    block_state = 0
    '''
    States:
    0 - no diff block
    1 - A part
    2 - B part

    0
    <<<<<<<
    1
    =======
    2
    >>>>>>>
    0
    '''
    block_prev_action = KEEP

    for action, line in diffs:

        if block_state == 0 and action == REMOVE:
            block_state = 1
            lines.append(block_start)
        elif block_state == 0 and action == INSERT:
            block_state = 2
            lines.append(block_start)
            lines.append(block_sep)
        elif block_state == 1 and action != KEEP and action != block_prev_action:
            block_state = 2
            lines.append(block_sep)
        elif block_state == 1 and action == KEEP:
            block_state = 0
            lines.append(block_sep)
            lines.append(block_end)
        elif block_state == 2 and (action == KEEP or action != block_prev_action):
            block_state = 0
            lines.append(block_end)

        print(action, line, block_state)

        lines.append(line)

        block_prev_action = action

    return '\n'.join(lines)


if __name__ == '__main__':
    aa = """
aa
bb

cc
dd
ee
    """.strip()

    bb = """
bb
cc
dd
eee
    """.strip()

    diff = git_diff_resolve(aa, bb, auto_resolve=None)
    print('.' * 14)
    print(diff)
