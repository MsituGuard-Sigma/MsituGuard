from django.contrib.admin.sites import AdminSite
from django.contrib.auth.models import User
from django.test import RequestFactory, SimpleTestCase, TestCase

from .admin import ReportAdmin, verify_reports
from .forms import ProfileForm
from .models import County, Profile, Report
from .urls import urlpatterns
from .utils import detect_nearest_county, get_confidence_label, get_risk_label


class UtilityTests(TestCase):
    def test_risk_labels_are_clean_ascii_text(self):
        self.assertEqual(get_risk_label(80), "Low Risk - Good Conditions")
        self.assertEqual(get_risk_label(65), "Moderate Risk - Extra Care Needed")
        self.assertEqual(get_risk_label(30), "High Risk - Challenging Conditions")

    def test_confidence_labels(self):
        self.assertEqual(get_confidence_label(has_weather=True, used_ml=True), "High")
        self.assertEqual(get_confidence_label(has_weather=True, used_ml=False), "Moderate")
        self.assertEqual(get_confidence_label(has_weather=False, used_ml=True), "Moderate")
        self.assertEqual(get_confidence_label(has_weather=False, used_ml=False), "Low")

    def test_nearest_county_falls_back_to_nairobi_when_no_counties_exist(self):
        self.assertEqual(detect_nearest_county(-1.286389, 36.817223), "Nairobi")

    def test_nearest_county_uses_county_coordinates(self):
        County.objects.create(name="Nairobi", latitude=-1.286389, longitude=36.817223)
        County.objects.create(name="Mombasa", latitude=-4.043477, longitude=39.668206)

        self.assertEqual(detect_nearest_county(-1.3, 36.8), "Nairobi")


class UrlConfigTests(SimpleTestCase):
    def test_predict_tree_survival_api_route_is_not_duplicated(self):
        matches = [
            pattern
            for pattern in urlpatterns
            if str(pattern.pattern) == "api/predict-tree-survival/"
        ]
        self.assertEqual(len(matches), 1)


class ProfileFormTests(TestCase):
    def test_profile_location_help_text_matches_environmental_domain(self):
        user = User.objects.create_user(username="mina", password="pass")
        Profile.objects.get_or_create(user=user)

        form = ProfileForm(instance=user.profile)

        self.assertEqual(
            form.fields["location"].help_text,
            "Your current location for environmental response",
        )


class ReportAdminTests(TestCase):
    def test_verify_reports_action_marks_reports_as_verified(self):
        user = User.objects.create_user(username="reviewer", password="pass")
        report = Report.objects.create(
            reporter=user,
            title="Illegal Logging Report",
            description="Trees being cut near the ridge",
            report_type="illegal_logging",
            location_name="Aberdare edge",
            phoneNumber="+254700000000",
            status="new",
        )
        request = RequestFactory().post("/")

        verify_reports(ReportAdmin, request, Report.objects.filter(pk=report.pk))

        report.refresh_from_db()
        self.assertEqual(report.status, "verified")

    def test_report_admin_risk_level_reads_stored_probability(self):
        report = Report(
            title="Fire Report",
            description="Smoke visible [ML_PROBABILITY:75.5]",
            report_type="fire",
            location_name="Forest block A",
            phoneNumber="+254700000000",
        )
        admin = ReportAdmin(Report, AdminSite())

        self.assertEqual(admin.risk_level(report), "High risk")
