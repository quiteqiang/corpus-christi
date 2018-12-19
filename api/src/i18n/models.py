import os
import re

from flask import json
from flask_marshmallow import Schema
from marshmallow import fields, ValidationError, validates
from marshmallow.validate import Length

from .. import orm
from ..shared.models import StringTypes


# ---- Locale

class I18NLocale(orm.Model):
    """Translation locale (e.g., 'en-us', 'es')"""
    __tablename__ = 'i18n_locale'
    code = orm.Column(StringTypes.LOCALE_CODE, primary_key=True)
    desc = orm.Column(StringTypes.MEDIUM_STRING, nullable=False)

    def __repr__(self):
        return f"<I18NLocale(id='{self.id}',desc='{self.desc}')>"


class I18NLocaleSchema(Schema):
    code = fields.String(required=True, validate=[Length(min=2, max=5)])
    desc = fields.String(required=True, validate=[Length(min=2)])

    @validates('code')
    def validate_id(self, code):
        if not re.fullmatch(r'[a-z]{2}-[A-Z]{2}', code, re.IGNORECASE):
            raise ValidationError('Invalid locale code')


# ---- Key

class I18NKey(orm.Model):
    """Key for a translatable string (e.g., 'groups.home_group')"""
    __tablename__ = 'i18n_key'
    id = orm.Column(StringTypes.I18N_KEY, primary_key=True)
    desc = orm.Column(StringTypes.LONG_STRING, nullable=False)

    def __repr__(self):
        return f"<I18NKey(key='{self.id}')>"


class I18NKeySchema(Schema):
    id = fields.String(required=True)
    desc = fields.String(required=True)

    @validates('id')
    def validate_id(self, id):
        if not re.fullmatch(r'[a-z]+[a-z.]*[a-z]', id, re.IGNORECASE):
            raise ValidationError("Invalid id; should be of form 'abc.def.xyz'")


# ---- Value

class I18NValue(orm.Model):
    """Language-specific value for a given I18NKey."""
    __tablename__ = 'i18n_value'
    key_id = orm.Column(StringTypes.I18N_KEY, orm.ForeignKey('i18n_key.id'), primary_key=True)
    locale_code = orm.Column(StringTypes.LOCALE_CODE, orm.ForeignKey('i18n_locale.code'), primary_key=True)
    gloss = orm.Column(orm.Text(), nullable=False)

    key = orm.relationship('I18NKey', backref='values', lazy=True)
    locale = orm.relationship('I18NLocale', backref='values', lazy=True)

    def __repr__(self):
        return f"<I18NValue(gloss='{self.gloss}')>"


class I18NValueSchema(Schema):
    key_id = fields.String(required=True)
    locale_code = fields.String(required=True)
    gloss = fields.String(required=True)


# ---- Language

class Language(orm.Model):
    """Language by ISO 639-1 language code"""
    __tablename__ = 'i18n_language'
    code = orm.Column(orm.String(2), primary_key=True)
    name_i18n = orm.Column(StringTypes.I18N_KEY, orm.ForeignKey('i18n_key.id'), nullable=False)
    key = orm.relationship('I18NKey', backref='languages', lazy=True)

    def __repr__(self):
        return f"<Language(code='{self.code}',name='{self.name_i18n}')>"

    @classmethod
    def load_from_file(cls, file_name='language-codes.json', locale_code='en-US'):
        count = 0
        file_path = os.path.abspath(os.path.join(__file__, os.path.pardir, 'data', file_name))

        if not I18NLocale.query.get(locale_code):
            orm.session.add(I18NLocale(code=locale_code, desc='English US'))

        with open(file_path, 'r') as fp:
            languages = json.load(fp)

            for language in languages:
                language_code = language['alpha2']
                language_name = language['English']

                name_i18n = f'language.name.{language_code}'
                i18n_create(name_i18n, locale_code,
                            language_name, description=f"Language {language_name}")

                orm.session.add(cls(code=language_code, name_i18n=name_i18n))
                count += 1
            orm.session.commit()
        return count


class LanguageSchema(Schema):
    code = fields.String(required=True, validate=[Length(equal=2)])
    name = fields.String(required=True, validate=[Length(min=2)])


# ---- CRUD


def i18n_create(key_id, locale_code, gloss, description=None):
    """Create a new value in the I18N database.

    In most cases, `description` can be omitted. It's only required
    if the I18NKey doesn't already exist.
    """
    result = i18n_check(key_id, locale_code)
    if result is not None:
        # Already in the DB, so we can't create it.
        raise RuntimeError(f"Value {key_id}/{locale_code} already exists")

    if I18NLocale.query.get(locale_code) is None:
        # The locale isn't present; something must be horribly wrong.
        raise RuntimeError(f"No locale {locale_code}")

    try:
        # Create the key if necessary.
        key = I18NKey.query.get(key_id)
        if key is None:
            if description is None:
                raise RuntimeError(f"Won't create key {key_id} without description")
            orm.session.add(I18NKey(id=key_id, desc=description))

        # Add the value
        orm.session.add(I18NValue(key_id=key_id, locale_code=locale_code, gloss=gloss))

        orm.session.commit()
    except Exception:
        orm.session.rollback()
        raise


def i18n_read(key_id, locale_code):
    """Read an existing value from the database."""
    result = i18n_check(key_id, locale_code)
    if result is None:
        raise RuntimeError(f"No value for {key_id}/{locale_code}")
    return result


def i18n_update(key_id, locale_code, gloss):
    """Update an existing value in the I18N database."""
    result = i18n_check(key_id, locale_code)
    if result is None:
        # Not in the DB; bail.
        raise RuntimeError(f"Value {key_id}/{locale_code} doesn't exist")
    result.gloss = gloss
    orm.session.commit()


def i18n_delete(key_id, locale_code):
    """Delete an existing value."""
    result = i18n_check(key_id, locale_code)
    if result is None:
        raise RuntimeError(f"Value {key_id}/{locale_code} doesn't exist")
    orm.session.delete(result)
    orm.session.commit()


def i18n_check(key_id, locale_code):
    """Check whether there's a value with the given key and locale."""
    return I18NValue.query.filter_by(key_id=key_id, locale_code=locale_code).first()
