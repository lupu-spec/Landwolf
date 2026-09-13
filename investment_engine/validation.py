def validate_model(model):
    if not model.property_id:
        raise ValueError("property_id required")
    if model.inspection_quality < 0 or model.inspection_quality > 1:
        raise ValueError("inspection_quality must be between 0 and 1")
    for name in ("government_costs","liens","repairs"):
        if getattr(model, name) is None:
            raise ValueError(f"{name} cannot be None")
    return True


class ModelValidator:
    __call__ = staticmethod(validate_model)
