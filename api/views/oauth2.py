import time
from flask import Blueprint, request, session, url_for
from flask import redirect, jsonify
from werkzeug.security import gen_salt
from authlib.integrations.flask_oauth2 import current_token
from authlib.oauth2 import OAuth2Error
from api.models import db, Person, OAuth2Client
from api.oauth2 import authorization, require_oauth


bp = Blueprint(__name__, 'home')


def current_person():
    if 'id' in session:
        uid = session['id']
        return Person.query.get(uid)
    return None


def split_by_crlf(s):
    return [v for v in s.splitlines() if v]

@bp.route('/logout')
def logout():
    del session['id']
    return redirect('/')


@bp.route('/create_client', methods=['POST'])
def create_client():
    person = current_person()
    if not person:
        return redirect('/')

    client_id = gen_salt(24)
    client_id_issued_at = int(time.time())
    client = OAuth2Client(
        client_id=client_id,
        client_id_issued_at=client_id_issued_at,
        person_id=person.id,
    )

    form = request.form
    client_metadata = {
        "client_name": form["client_name"],
        "client_uri": form["client_uri"],
        "grant_types": split_by_crlf(form["grant_type"]),
        "redirect_uris": split_by_crlf(form["redirect_uri"]),
        "response_types": split_by_crlf(form["response_type"]),
        "scope": form["scope"],
        "token_endpoint_auth_method": form["token_endpoint_auth_method"]
    }
    client.set_client_metadata(client_metadata)

    if form['token_endpoint_auth_method'] == 'none':
        client.client_secret = ''
    else:
        client.client_secret = gen_salt(48)

    db.session.add(client)
    db.session.commit()
    return redirect('/')


@bp.route('/oauth/authorize', methods=['POST'])
def authorize():
    person = current_person()
    # if person log status is not true (Auth server), then to log it in
    if not person:
        return redirect(url_for('website.routes.home', next=request.url))
        
    if not person and 'personname' in request.form:
        personname = request.form.get('personname')
        person = Person.query.filter_by(personname=personname).first()
    if request.form['confirm']:
        grant_person = person
    else:
        grant_person = None
    return authorization.create_authorization_response(grant_person=grant_person)


@bp.route('/oauth/token', methods=['POST'])
def issue_token():
    return authorization.create_token_response()


@bp.route('/oauth/revoke', methods=['POST'])
def revoke_token():
    return authorization.create_endpoint_response('revocation')


@bp.route('/api/me')
@require_oauth('profile')
def api_me():
    person = current_token.person
    return jsonify(id=person.id, personname=person.personname)