# forms.py
from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileAllowed, FileRequired
from wtforms import SubmitField

class CSVUploadForm(FlaskForm):
    csv_file = FileField('Upload CSV', validators=[
        FileRequired(),
        FileAllowed(['csv'], 'CSV Files only!')
    ])
    submit = SubmitField('Upload')
