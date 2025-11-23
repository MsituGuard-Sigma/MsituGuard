from django.db.models import Count
from django.utils import timezone
from datetime import timedelta
from .models import User, Tree


# Total number of trees in the system
def get_total_trees():
    return Tree.objects.count()


# Count of users by type
def get_user_counts():
    return {
        "individuals": User.objects.filter(user_type=User.INDIVIDUAL).count(),
        "organisations": User.objects.filter(user_type=User.ORGANISATION).count(),
    }


# Leaderboard: Top users by tree_count
def get_leaderboard(limit=10):
    return User.objects.order_by('-tree_count')[:limit]


# Badge distribution: Count of users per badge
def get_badge_distribution():
    badges = ["None", "Bronze", "Silver", "Gold", "Diamond"]
    return {badge: User.objects.filter(badge=badge).count() for badge in badges}


# Monthly tree uploads for the past N months (default 6)
def get_monthly_tree_uploads(months=6):
    today = timezone.now().date()
    data = []

    for i in range(months):
        month_start = today - timedelta(days=30 * (i + 1))
        month_end = today - timedelta(days=30 * i)
        count = Tree.objects.filter(
            uploaded_at__gte=month_start,
            uploaded_at__lt=month_end
        ).count()
        data.append({
            "month": month_end.strftime("%B %Y"),
            "trees_uploaded": count
        })

    return list(reversed(data))


# Organisation analytics: Returns list of org users with tree counts
def get_org_analytics():
    return User.objects.filter(
        user_type=User.ORGANISATION
    ).values("username", "tree_count").order_by("-tree_count")


# Individual analytics: Returns list of individual users with tree counts
def get_individual_analytics():
    return User.objects.filter(
        user_type=User.INDIVIDUAL
    ).values("username", "tree_count").order_by("-tree_count")
