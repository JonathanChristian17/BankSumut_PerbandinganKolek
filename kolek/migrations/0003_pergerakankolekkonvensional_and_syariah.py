# Generated manually to ensure SAFE rename
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('kolek', '0002_alter_pergerakankolek_id'),
    ]

    operations = [
        # 1. Rename the model (this renames the database table safely without data loss)
        migrations.RenameModel(
            old_name='PergerakanKolek',
            new_name='PergerakanKolekKonvensional',
        ),
        # 2. Update Model Options
        migrations.AlterModelOptions(
            name='pergerakankolekkonvensional',
            options={'ordering': ['tanggal_upload', 'accnbr'], 'verbose_name': 'Pergerakan Kolek Konvensional', 'verbose_name_plural': 'Pergerakan Kolek Konvensional'},
        ),
        # 3. Rename old fields mapping to new names
        migrations.RenameField(
            model_name='pergerakankolekkonvensional',
            old_name='rating_kolek',
            new_name='kelompok_sandi',
        ),
        migrations.RenameField(
            model_name='pergerakankolekkonvensional',
            old_name='rek_kredit',
            new_name='accnbr',
        ),
        migrations.RenameField(
            model_name='pergerakankolekkonvensional',
            old_name='nama',
            new_name='cifnm',
        ),
        migrations.RenameField(
            model_name='pergerakankolekkonvensional',
            old_name='cabang',
            new_name='branchid',
        ),
        migrations.RenameField(
            model_name='pergerakankolekkonvensional',
            old_name='hr_tungg_bunga',
            new_name='hr_tungg_margin',
        ),
        # 4. (nilai_wajar already exists in DB, so no AddField needed for it!)
        # 5. Update unique together constraint based on renamed fields
        migrations.AlterUniqueTogether(
            name='pergerakankolekkonvensional',
            unique_together={('accnbr', 'tanggal_upload')},
        ),
        # 6. Create the entirely new Syariah table
        migrations.CreateModel(
            name='PergerakanKolekSyariah',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('tanggal_upload', models.DateField()),
                ('kelompok_sandi', models.CharField(max_length=50)),
                ('accnbr', models.BigIntegerField()),
                ('cifid', models.CharField(max_length=50)),
                ('cifnm', models.TextField()),
                ('branchid', models.IntegerField()),
                ('plafond', models.DecimalField(decimal_places=2, max_digits=18)),
                ('saldo_akhir', models.DecimalField(decimal_places=2, max_digits=18)),
                ('nilai_wajar', models.DecimalField(decimal_places=2, default=0, max_digits=18)),
                ('hr_tungg_pokok', models.IntegerField(default=0)),
                ('hr_tungg_margin', models.IntegerField(default=0)),
                ('kolek', models.IntegerField(default=0)),
            ],
            options={
                'verbose_name': 'Pergerakan Kolek Syariah',
                'verbose_name_plural': 'Pergerakan Kolek Syariah',
                'ordering': ['tanggal_upload', 'accnbr'],
                'unique_together': {('accnbr', 'tanggal_upload')},
            },
        ),
    ]
