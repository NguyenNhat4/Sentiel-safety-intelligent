from vision.api import PpeVisionFacade


def test_ppe_detection_is_associated_only_with_the_containing_person():
    people = [(10, 10, 30, 80, 0.9), (60, 10, 30, 80, 0.9)]

    assert PpeVisionFacade._person_containing(25, 25, people) == 0
    assert PpeVisionFacade._person_containing(75, 25, people) == 1
    assert PpeVisionFacade._person_containing(50, 25, people) is None
