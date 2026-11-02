from .forms import REGISTRY


def navigation(request):
    membership = (
        getattr(request.user, "membership", None)
        if request.user.is_authenticated
        else None
    )
    return {
        "membership": membership,
        "navigation": [(k, title) for k, (_, title) in REGISTRY.items()],
    }
