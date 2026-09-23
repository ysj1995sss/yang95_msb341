from resume_tailorer.parsers.anchor_detection import find_anchor_blocks


def _is_bullet(line: str) -> bool:
    return line.strip().startswith(("•", "-"))


def test_finds_single_job_block():
    lines = [
        "Marketing Manager",
        "Acme Corp | Remote    2022-2024",
        "- Did a thing",
        "- Did another thing",
    ]
    blocks = find_anchor_blocks(lines, get_text=lambda l: l, is_bullet=_is_bullet)
    assert len(blocks) == 1
    block = blocks[0]
    assert block.anchor_index == 1
    assert block.title_index == 0
    assert block.body_indices == [2, 3]


def test_finds_multiple_job_blocks_and_trims_trailing_title():
    lines = [
        "Marketing Manager",
        "Acme Corp | Remote    2022-2024",
        "- Bullet one",
        "Operations Lead",  # this is job 2's title -- must be trimmed from job 1's bullets
        "Beta Inc | NYC    2019-2021",
        "- Bullet two",
    ]
    blocks = find_anchor_blocks(lines, get_text=lambda l: l, is_bullet=_is_bullet)
    assert len(blocks) == 2
    assert blocks[0].body_indices == [2]  # "Operations Lead" excluded
    assert blocks[1].anchor_index == 4
    assert blocks[1].title_index == 3
    assert blocks[1].body_indices == [5]


def test_title_lookback_hits_a_bullet_first_yields_no_title():
    lines = [
        "- A bullet from the previous job",
        "Acme Corp | Remote    2022-2024",
        "- Bullet one",
    ]
    blocks = find_anchor_blocks(lines, get_text=lambda l: l, is_bullet=_is_bullet)
    assert blocks[0].title_index is None


def test_blank_lines_are_skipped_for_title_lookback():
    lines = [
        "Marketing Manager",
        "",
        "Acme Corp | Remote    2022-2024",
        "- Bullet one",
    ]
    blocks = find_anchor_blocks(lines, get_text=lambda l: l, is_bullet=_is_bullet)
    assert blocks[0].title_index == 0


def test_body_indices_include_non_bullet_continuation_lines():
    """body_indices is deliberately unfiltered -- the PDF-text caller needs
    to see wrapped continuation lines (no bullet marker) to merge them into
    the previous bullet; only a caller with real per-paragraph bullets
    (DOCX) should filter this down to is_bullet(...) itself."""
    lines = [
        "Marketing Manager",
        "Acme Corp | Remote    2022-2024",
        "- Did a thing that wraps onto",
        "a second physical line",
    ]
    blocks = find_anchor_blocks(lines, get_text=lambda l: l, is_bullet=_is_bullet)
    assert blocks[0].body_indices == [2, 3]


def test_no_anchors_returns_empty_list():
    lines = ["Just some text", "- a bullet", "no years here"]
    blocks = find_anchor_blocks(lines, get_text=lambda l: l, is_bullet=_is_bullet)
    assert blocks == []
