# Generated by Django 5.2.3 on 2025-06-16 19:49

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='Store',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=100)),
                ('location', models.CharField(max_length=255)),
                ('owner', models.ForeignKey(limit_choices_to={'role': 'head_manager'}, on_delete=django.db.models.deletion.CASCADE, related_name='owned_stores', to=settings.AUTH_USER_MODEL)),
            ],
        ),
        migrations.CreateModel(
            name='StoreCashier',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('is_active', models.BooleanField(default=True)),
                ('assigned_at', models.DateTimeField(auto_now_add=True)),
                ('cashier', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='cashier_store', to=settings.AUTH_USER_MODEL)),
                ('store', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='cashier_assignment', to='store.store')),
            ],
        ),
        migrations.CreateModel(
            name='StoreManager',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('is_active', models.BooleanField(default=True)),
                ('assigned_at', models.DateTimeField(auto_now_add=True)),
                ('manager', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='managed_store', to=settings.AUTH_USER_MODEL)),
                ('store', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='manager_assignment', to='store.store')),
            ],
        ),
    ]
