from services.working_intervals_domain import normalize_intervals


def test_normalize_moves_right_neighbor_start_when_overlap():
    result = normalize_intervals(
        {
            1: (540, 900),
            2: (780, 1020),
            3: (1020, 1260),
        },
        edited_idx=1,
    )

    assert result == {
        1: (540, 900),
        2: (900, 1020),
        3: (1020, 1260),
    }


def test_normalize_disables_right_neighbor_when_fully_covered():
    result = normalize_intervals(
        {
            1: (540, 1100),
            2: (780, 1020),
            3: (1020, 1260),
        },
        edited_idx=1,
    )

    assert result == {
        1: (540, 1100),
        2: (None, None),
        3: (1100, 1260),
    }


def test_normalize_moves_left_neighbor_end_when_overlap():
    result = normalize_intervals(
        {
            1: (540, 720),
            2: (700, 900),
            3: (1020, 1260),
        },
        edited_idx=2,
    )

    assert result == {
        1: (540, 700),
        2: (700, 900),
        3: (1020, 1260),
    }


def test_normalize_uses_nearest_active_neighbor_over_gap():
    result = normalize_intervals(
        {
            1: (540, 1200),
            2: (None, None),
            3: (1020, 1260),
        },
        edited_idx=1,
    )

    assert result == {
        1: (540, 1200),
        2: (None, None),
        3: (1200, 1260),
    }


def test_normalize_case_edit_1_end_to_14_moves_interval_2_start_to_14():
    result = normalize_intervals(
        {
            1: (540, 840),  # 09:00-14:00
            2: (780, 1020),  # 13:00-17:00
            3: (None, None),
        },
        edited_idx=1,
    )

    assert result == {
        1: (540, 840),
        2: (840, 1020),
        3: (None, None),
    }


def test_normalize_case_edit_2_start_to_11_moves_interval_1_end_to_11():
    result = normalize_intervals(
        {
            1: (540, 720),  # 09:00-12:00
            2: (660, 1020),  # 11:00-17:00
            3: (None, None),
        },
        edited_idx=2,
    )

    assert result == {
        1: (540, 660),
        2: (660, 1020),
        3: (None, None),
    }


def test_normalize_stitching_keeps_touching_boundaries():
    result = normalize_intervals(
        {
            1: (540, 780),
            2: (780, 1020),
            3: (1020, 1260),
        },
        edited_idx=2,
    )

    assert result == {
        1: (540, 780),
        2: (780, 1020),
        3: (1020, 1260),
    }


def test_normalize_absorbs_right_when_equal_end():
    result = normalize_intervals(
        {
            1: (540, 1020),
            2: (780, 1020),
            3: (None, None),
        },
        edited_idx=1,
    )

    assert result == {
        1: (540, 1020),
        2: (None, None),
        3: (None, None),
    }


def test_normalize_case_edit_1_end_to_18_disables_2_and_moves_3_start_to_18():
    result = normalize_intervals(
        {
            1: (540, 1080),  # 09:00-18:00
            2: (780, 1020),  # 13:00-17:00
            3: (1020, 1260),  # 17:00-21:00
        },
        edited_idx=1,
    )

    assert result == {
        1: (540, 1080),
        2: (None, None),
        3: (1080, 1260),
    }


def test_normalize_case_edit_2_end_to_20_moves_3_start_to_20():
    result = normalize_intervals(
        {
            1: (540, 720),
            2: (780, 1200),  # 13:00-20:00
            3: (1020, 1260),  # 17:00-21:00
        },
        edited_idx=2,
    )

    assert result == {
        1: (540, 720),
        2: (780, 1200),
        3: (1200, 1260),
    }
