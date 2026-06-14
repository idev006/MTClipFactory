from __future__ import annotations


class RecipeAlreadyExistsError(ValueError):
    """Raised when a recipe code already exists."""


class RecipeNotFoundError(ValueError):
    """Raised when a recipe does not exist."""


class RecipeAssetMismatchError(ValueError):
    """Raised when an asset belongs to a different product than the recipe."""


class AssetNotReadyForRecipeError(ValueError):
    """Raised when an asset is not ready to be used in a recipe."""


class RecipeItemAlreadyExistsError(ValueError):
    """Raised when the same asset role is already present in a recipe."""


class PreviewBuildInputError(ValueError):
    """Raised when a preview job cannot be built from current recipe state."""


class OutputNotFoundError(ValueError):
    """Raised when an output cannot be found."""


class OutputApprovalError(ValueError):
    """Raised when an output cannot be approved for the current recipe state."""


class RecipeApprovalError(ValueError):
    """Raised when a recipe approval decision is invalid."""


class FinalRenderPrerequisiteError(ValueError):
    """Raised when final render requirements are not satisfied."""


class FactoryJobNotFoundError(ValueError):
    """Raised when a factory job cannot be found."""
