# Generated by Django 4.1 on 2023-06-01 18:07

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('users', 'create_superuser'),
    ]

    operations = [
        migrations.AlterField(
            model_name='customuser',
            name='photo',
            field=models.ImageField(blank=True, null=True, upload_to='users/photo/', verbose_name='Users Photo'),
        ),
    ]