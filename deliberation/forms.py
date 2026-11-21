from django import forms

from .models import Comment, Document


class DocumentForm(forms.ModelForm):
    class Meta:
        model = Document
        fields = ("title", "summary", "course", "department")
        widgets = {"summary": forms.Textarea(attrs={"rows": 3})}

    def __init__(self, *args, kind, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["department"].queryset = self.fields["department"].queryset.select_related("faculty")
        self.fields["department"].empty_label = "Whole university"
        if kind == Document.Kind.POLICY:
            self.fields.pop("course")
        else:
            self.fields["course"].required = True
            self.fields["course"].label = "Course to redesign"


class CommentForm(forms.ModelForm):
    class Meta:
        model = Comment
        fields = ("kind", "section", "body", "anonymous")
        labels = {"kind": "Type", "section": "About", "body": "Your comment", "anonymous": "Post anonymously"}
        widgets = {"body": forms.Textarea(attrs={"rows": 3})}

    def __init__(self, *args, document, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["section"].queryset = document.sections.all()
        self.fields["section"].required = False
        self.fields["section"].empty_label = "The whole document"


class SectionEditForm(forms.Form):
    body = forms.CharField(required=False, widget=forms.Textarea(attrs={"class": "tall"}), label="Text")
    note = forms.CharField(required=False, max_length=200, label="What did you change? (optional)")
    base_version = forms.IntegerField(widget=forms.HiddenInput)


class SectionAddForm(forms.Form):
    title = forms.CharField(max_length=120, label="New section title")
