import pytest
from scidoc_core.bbox import BBox


def test_bbox_scale_normalize_and_iou() -> None:
    box = BBox.from_list([10, 20, 110, 220])
    assert box.area == 20_000
    assert box.scale(2).as_list() == [20, 40, 220, 440]
    assert box.normalized(200, 400).as_list() == [0.05, 0.05, 0.55, 0.55]
    assert box.iou(box) == 1


def test_bbox_rejects_reversed_coordinates() -> None:
    with pytest.raises(ValueError):
        BBox.from_list([10, 20, 5, 25])
