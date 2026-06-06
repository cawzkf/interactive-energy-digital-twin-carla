"""Unit tests for the layered exception hierarchy, structured as Arrange-Act-Assert."""
from src.exceptions import (
    AcquisitionSourceError,
    ApplicationError,
    DomainError,
    InfraError,
    InvalidParameterError,
    MarchForceError,
    MessageBusError,
    ProcessingError,
    RepositoryError,
)


class TestHierarchy:
    def test_layer_bases_inherit_from_root(self):
        # Assert
        assert issubclass(DomainError, MarchForceError)
        assert issubclass(InfraError, MarchForceError)
        assert issubclass(ApplicationError, MarchForceError)

    def test_infra_errors_share_infra_base(self):
        # Assert
        assert issubclass(MessageBusError, InfraError)
        assert issubclass(RepositoryError, InfraError)
        assert issubclass(AcquisitionSourceError, InfraError)

    def test_domain_and_application_specializations(self):
        # Assert
        assert issubclass(InvalidParameterError, DomainError)
        assert issubclass(ProcessingError, ApplicationError)


class TestCatching:
    def test_specific_error_caught_by_layer_base(self):
        # Arrange / Act
        try:
            raise RepositoryError("boom")
        except InfraError as caught:
            message = str(caught)
        # Assert
        assert message == "boom"
