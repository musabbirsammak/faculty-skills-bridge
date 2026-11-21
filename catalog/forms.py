from django import forms
from django.forms import BaseInlineFormSet, inlineformset_factory

from .models import Course, CourseSkill, Skill


class SkillForm(forms.ModelForm):
    class Meta:
        model = Skill
        fields = ("name", "family", "aliases", "description", "related")
        widgets = {
            "description": forms.Textarea(attrs={"rows": 3}),
            "related": forms.SelectMultiple(attrs={"size": 8}),
        }
        help_texts = {"related": "Optional. Hold Ctrl (Cmd on Mac) to pick several."}

    def clean_name(self):
        name = self.cleaned_data["name"].strip()
        clash = Skill.objects.filter(name__iexact=name).exclude(pk=self.instance.pk)
        if clash.exists():
            raise forms.ValidationError("This skill is already in the list.")
        return name


class CourseForm(forms.ModelForm):
    class Meta:
        model = Course
        fields = ("title", "area", "description", "emerging", "impact", "impact_note", "source")
        widgets = {"description": forms.Textarea(attrs={"rows": 3})}


class RequirementForm(forms.ModelForm):
    # Unticked by default so that empty extra rows count as unchanged and are ignored.
    core = forms.BooleanField(required=False, initial=False, label="Core")

    class Meta:
        model = CourseSkill
        fields = ("skill", "core")


class RequirementFormSet(BaseInlineFormSet):
    def clean(self):
        super().clean()
        kept = [f.cleaned_data for f in self.forms if f.cleaned_data and not f.cleaned_data.get("DELETE")]
        skills = [d["skill"] for d in kept if d.get("skill")]
        if not skills:
            raise forms.ValidationError("Add at least one skill.")
        if len(skills) != len(set(skills)):
            raise forms.ValidationError("Each skill can appear only once.")
        if not any(d.get("core") for d in kept if d.get("skill")):
            raise forms.ValidationError("Mark at least one skill as core.")


RequirementFormSetFactory = inlineformset_factory(
    Course, CourseSkill, form=RequirementForm, formset=RequirementFormSet, extra=4, can_delete=True
)


class CourseStatusForm(forms.Form):
    status = forms.ChoiceField(choices=Course.Status.choices)
    department = forms.ModelChoiceField(queryset=None, required=False, empty_label="No department yet")
    note = forms.CharField(max_length=255, required=False, label="Why? (optional, shown in the history)")

    def __init__(self, *args, departments, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["department"].queryset = departments.select_related("faculty")
