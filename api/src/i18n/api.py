from flask import request, jsonify
from marshmallow import ValidationError

from . import i18n
from .models import I18NLocale, I18NLocaleSchema, I18NKeySchema, I18NKey, I18NValue, I18NValueSchema, \
    LanguageSchema, Language
from .. import orm

i18n_locale_schema = I18NLocaleSchema()
i18n_key_schema = I18NKeySchema()
i18n_value_schema = I18NValueSchema()
i18n_language_code_schema = LanguageSchema()


# ---- Locale

@i18n.route('/locales')
def read_all_locales():
    locales = I18NLocale.query.all()
    return i18n_locale_schema.jsonify(locales, many=True)


@i18n.route('/locales/<locale_code>')
def read_one_locale(locale_code):
    locale = I18NLocale.query.filter_by(code=locale_code).first()
    if locale is None:
        return 'No such locale', 404
    else:
        return i18n_locale_schema.jsonify(locale)


@i18n.route('/locales', methods=['POST'])
def create_locale():
    try:
        loaded = i18n_locale_schema.load(request.json)
    except ValidationError as err:
        return jsonify(err.messages), 422

    new_locale = I18NLocale(**request.json)
    orm.session.add(new_locale)
    orm.session.commit()
    return i18n_locale_schema.jsonify(new_locale), 201


@i18n.route('/locales/<locale_code>', methods=['DELETE'])
def delete_one_locale(locale_code):
    locale = I18NLocale.query.get_or_404(locale_code)
    orm.session.delete(locale)
    orm.session.commit()
    return 'ok', 204


# ---- Keys

@i18n.route('/keys')
def read_all_keys():
    keys = I18NKey.query.all()
    return i18n_key_schema.jsonify(keys, many=True)


@i18n.route('/keys/<key_id>')
def read_one_key(key_id):
    key = I18NKey.query.filter_by(id=key_id).first()
    if key is None:
        return 'No such key', 404
    else:
        return i18n_key_schema.jsonify(key)


@i18n.route('/keys', methods=['POST'])
def create_key():
    try:
        loaded = i18n_key_schema.load(request.json)
    except ValidationError as err:
        return jsonify(err.messages), 422

    new_key = I18NKey(**request.json)
    orm.session.add(new_key)
    orm.session.commit()
    return i18n_key_schema.jsonify(new_key), 201


# ---- Values

@i18n.route('/values')
def read_all_values():
    values = I18NValue.query.all()
    return i18n_value_schema.jsonify(values, many=True)


@i18n.route('/values/<locale_code>')
def read_xlation(locale_code):
    # Check that the locale exists.
    locale = I18NLocale.query.filter_by(code=locale_code).first()
    if locale is None:
        return 'Invalid locale', 404

    # Fetch the values for this locale
    values = I18NValue.query.filter_by(locale_code=locale_code)

    # Format the response.
    format = request.args.get('format', 'list')
    if format == 'list':
        # Return the values as a simple list.
        return i18n_value_schema.jsonify(values, many=True)
    elif format == 'tree':
        # Interpret keys as a hierarchical structure.
        # Tree-building idea from  https://stackoverflow.com/questions/16547643
        tree = {}
        for value in values:
            t = tree
            keys = value.key_id.split('.')
            for idx, key in enumerate(keys):
                if idx < len(keys) - 1:
                    # Intermediate "node"; add another dictionary
                    t = t.setdefault(key, {})
                else:
                    # Last node
                    if isinstance(t, dict):
                        # Set key-value in leaf node of tree
                        t[key] = value.gloss
                    else:
                        # Already a string value for this key
                        return f'Invalid key ({value.key_id})', 400
        return jsonify(tree)
    else:
        return 'Invalid format', 400


# ---- Languages

@i18n.route('/languages')
@i18n.route('/languages/<language_code>')
def read_languages(language_code=None):
    if language_code is None:
        result = Language.query.all()
        return i18n_language_code_schema.jsonify(result, many=True)
    else:
        result = Language.query.filter_by(code=language_code).first()
        return i18n_language_code_schema.jsonify(result)
