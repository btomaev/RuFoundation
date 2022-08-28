# Generated by Django 4.0.6 on 2022-08-28 19:40

from django.db import migrations, models
import django.utils.timezone


class Migration(migrations.Migration):

    dependencies = [
        ('web', '0022_remove_forumpost_deleted_at_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='forumpostversion',
            name='created_at',
            field=models.DateTimeField(auto_now_add=True, default=django.utils.timezone.now, verbose_name='Время создания'),
            preserve_default=False,
        ),
    ]