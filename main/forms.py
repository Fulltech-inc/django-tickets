# -*- coding: utf-8 -*-

from django import forms
from django.contrib.auth.models import User
from .models import Category, Ticket, FollowUp, Attachment
from django.http import JsonResponse
from .models import Category



class UserSettingsForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ('first_name', 'last_name', 'email')


class TicketCreateForm(forms.ModelForm):
    class Meta:
        model = Ticket
        fields = ('interaction_id', 'category', 'sub_category', 'title', 'description', 'assigned_to')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Main category — only top-level (no parent)
        self.fields['category'].queryset = Category.objects.filter(
            is_active=True, parent=None
        )
        self.fields['category'].empty_label = 'Select main category...'
        self.fields['category'].required = True

        # Sub category — start empty, JS will populate
        self.fields['sub_category'].queryset = Category.objects.none()
        self.fields['sub_category'].empty_label = 'Select sub category...'
        self.fields['sub_category'].required = True

        # If form is being reloaded with data (e.g. validation error), repopulate subs
        if 'category' in self.data:
            try:
                main_id = int(self.data.get('category'))
                self.fields['sub_category'].queryset = Category.objects.filter(
                    is_active=True, parent_id=main_id
                )
            except (ValueError, TypeError):
                pass
        elif self.instance.pk and self.instance.category:
            self.fields['sub_category'].queryset = Category.objects.filter(
                is_active=True, parent=self.instance.category
            )


class TicketEditForm(forms.ModelForm):
    class Meta:
        model = Ticket
        fields = ('interaction_id', 'category', 'sub_category', 'title', 'description', 'status', 'waiting_for', 'assigned_to')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.fields['category'].queryset = Category.objects.filter(
            is_active=True, parent=None
        )
        self.fields['category'].empty_label = 'Select main category...'
        self.fields['category'].required = False

        self.fields['sub_category'].queryset = Category.objects.none()
        self.fields['sub_category'].empty_label = 'Select sub category...'
        self.fields['sub_category'].required = False

        if 'category' in self.data:
            try:
                main_id = int(self.data.get('category'))
                self.fields['sub_category'].queryset = Category.objects.filter(
                    is_active=True, parent_id=main_id
                )
            except (ValueError, TypeError):
                pass
        elif self.instance.pk and self.instance.category:
            self.fields['sub_category'].queryset = Category.objects.filter(
                is_active=True, parent=self.instance.category
            )


class FollowupForm(forms.ModelForm):
    class Meta:
        model = FollowUp
        fields = ('ticket', 'title', 'text', 'user')


class AttachmentForm(forms.ModelForm):
    class Meta:
        model = Attachment
        fields = ('file',)