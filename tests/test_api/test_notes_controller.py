"""
Copyright ©2022. The Regents of the University of California (Regents). All Rights Reserved.

Permission to use, copy, modify, and distribute this software and its documentation
for educational, research, and not-for-profit purposes, without fee and without a
signed licensing agreement, is hereby granted, provided that the above copyright
notice, this paragraph and the following two paragraphs appear in all copies,
modifications, and distributions.

Contact The Office of Technology Licensing, UC Berkeley, 2150 Shattuck Avenue,
Suite 510, Berkeley, CA 94720-1620, (510) 643-7201, otl@berkeley.edu,
http://ipira.berkeley.edu/industry-info for commercial licensing opportunities.

IN NO EVENT SHALL REGENTS BE LIABLE TO ANY PARTY FOR DIRECT, INDIRECT, SPECIAL,
INCIDENTAL, OR CONSEQUENTIAL DAMAGES, INCLUDING LOST PROFITS, ARISING OUT OF
THE USE OF THIS SOFTWARE AND ITS DOCUMENTATION, EVEN IF REGENTS HAS BEEN ADVISED
OF THE POSSIBILITY OF SUCH DAMAGE.

REGENTS SPECIFICALLY DISCLAIMS ANY WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE. THE
SOFTWARE AND ACCOMPANYING DOCUMENTATION, IF ANY, PROVIDED HEREUNDER IS PROVIDED
"AS IS". REGENTS HAS NO OBLIGATION TO PROVIDE MAINTENANCE, SUPPORT, UPDATES,
ENHANCEMENTS, OR MODIFICATIONS.
"""

from datetime import date, datetime
from time import sleep

from boac.lib.util import localize_datetime, utc_now
from boac.models.authorized_user import AuthorizedUser
from boac.models.cohort_filter import CohortFilter
from boac.models.curated_group import CuratedGroup
from boac.models.note import Note
from boac.models.note_attachment import NoteAttachment
from boac.models.note_read import NoteRead
import pytest
from tests.test_api.api_test_utils import all_cohorts_owned_by
from tests.util import mock_advising_note_s3_bucket, mock_legacy_note_attachment

asc_advisor_uid = '6446'
ce3_advisor_uid = '2525'
coe_advisor_uid = '1133399'
coe_advisor_no_advising_data_uid = '1022796'
coe_scheduler_uid = '6972201'
l_s_director_uid = '53791'
l_s_major_advisor_uid = '242881'
l_s_director_no_advising_data_uid = '1022796'
admin_uid = '2040'

coe_student = {
    'sid': '9000000000',
    'uid': '300847',
}


@pytest.fixture()
def mock_coe_advising_note():
    return Note.create(
        author_uid=coe_advisor_uid,
        author_name='Balloon Man',
        author_role='Spherical',
        author_dept_codes=['COENG'],
        body='He spattered me with tomatoes, Hummus, chick peas',
        sid=coe_student['sid'],
        subject='I was walking up Sixth Avenue',
    )


@pytest.fixture()
def mock_asc_advising_note(app, db):
    return Note.create(
        author_uid='1133399',
        author_name='Roberta Joan Anderson',
        author_role='Advisor',
        author_dept_codes=['COENG'],
        body="""
            She could see the valley barbecues from her window sill.
            See the blue pools in the squinting sun. Hear the hissing of summer lawns
        """,
        sid='3456789012',
        subject='The hissing of summer lawns',
        topics=['darkness', 'no color no contrast'],
    )


@pytest.fixture()
def mock_private_advising_note(app):
    with mock_advising_note_s3_bucket(app):
        base_dir = app.config['BASE_DIR']
        path_to_file = f'{base_dir}/fixtures/mock_advising_note_attachment_1.txt'
        with open(path_to_file, 'r') as file:
            return Note.create(
                attachments=[{'name': path_to_file.rsplit('/', 1)[-1], 'byte_stream': file.read()}],
                author_uid=ce3_advisor_uid,
                author_name='Kate Pierson',
                author_role='Advisor',
                author_dept_codes=['ZCEEE'],
                body='Underground like a wild potato.',
                is_private=True,
                sid=coe_student['sid'],
                subject='You\'re living in your own Private Idaho.',
            )


class TestGetNote:

    @classmethod
    def _api_note_by_id(cls, client, note_id, expected_status_code=200):
        response = client.get(f'/api/note/{note_id}')
        assert response.status_code == expected_status_code
        return response.json

    def test_not_authenticated(self, app, client, mock_coe_advising_note):
        """Returns 401 if not authenticated."""
        self._api_note_by_id(client=client, note_id=mock_coe_advising_note.id, expected_status_code=401)

    def test_user_without_advising_data_access(self, client, fake_auth, mock_coe_advising_note):
        """Denies access to a user who cannot access notes and appointments."""
        fake_auth.login(coe_advisor_no_advising_data_uid)
        self._api_note_by_id(client=client, note_id=mock_coe_advising_note.id, expected_status_code=401)

    def test_limited_access_to_private_note(self, client, fake_auth, mock_private_advising_note):
        fake_auth.login(coe_advisor_uid)
        api_json = self._api_note_by_id(client=client, note_id=mock_private_advising_note.id)
        assert 'Private Idaho' in api_json['subject']
        assert api_json['author']
        assert api_json['body'] is None

    def test_full_access_to_private_note(self, client, fake_auth, mock_private_advising_note):
        fake_auth.login(ce3_advisor_uid)
        api_json = self._api_note_by_id(client=client, note_id=mock_private_advising_note.id)
        assert 'Private Idaho' in api_json['subject']
        assert 'potato' in api_json['body']

    def test_get_note_by_id(self, app, client, fake_auth, mock_coe_advising_note):
        """Returns note in JSON compatible with BOA front-end."""
        fake_auth.login(admin_uid)
        note = self._api_note_by_id(client=client, note_id=mock_coe_advising_note.id)
        assert note
        assert 'id' in note
        assert note['type'] == 'note'
        assert note['body'] == note['message']
        assert note['read'] is False
        # Mark as read and re-test
        NoteRead.find_or_create(AuthorizedUser.get_id_per_uid(admin_uid), note['id'])
        assert self._api_note_by_id(client=client, note_id=mock_coe_advising_note.id)['read'] is True


class TestNoteCreation:

    def test_not_authenticated(self, app, client):
        """Returns 401 if not authenticated."""
        assert _api_note_create(
            app=app,
            author_id=AuthorizedUser.get_id_per_uid(coe_advisor_uid),
            body='This is the last night of the fair, And the grease in the hair',
            client=client,
            expected_status_code=401,
            sids=[coe_student['sid']],
            subject='Rusholme Ruffians',
        )

    def test_admin_user_is_not_authorized(self, app, client, fake_auth):
        """Returns 401 if user is an admin."""
        fake_auth.login(admin_uid)
        admin = AuthorizedUser.find_by_uid(admin_uid)
        assert _api_note_create(
            app=app,
            author_id=admin.id,
            body='This is the last night of the fair, And the grease in the hair',
            client=client,
            expected_status_code=403,
            sids=[coe_student['sid']],
            subject='Rusholme Ruffians',
        )

    def test_scheduler_is_not_authorized(self, app, client, fake_auth):
        """Returns 401 if user is a scheduler."""
        fake_auth.login(coe_scheduler_uid)
        admin = AuthorizedUser.find_by_uid(coe_scheduler_uid)
        assert _api_note_create(
            app=app,
            author_id=admin.id,
            body='Language made unintelligible by excessive use of abstruse technical terms.',
            client=client,
            expected_status_code=401,
            sids=[coe_student['sid']],
            subject='Gobbledygook',
        )

    def test_unauthorized_private_note(self, app, client, fake_auth):
        """Non-CE3 advisor cannot create a private note."""
        fake_auth.login(coe_advisor_uid)
        _api_note_create(
            app=app,
            author_id=AuthorizedUser.get_id_per_uid(coe_advisor_uid),
            body='She drove a Plymouth Satellite',
            client=client,
            expected_status_code=403,
            is_private=True,
            sids=[coe_student['sid']],
            subject='Planet Claire',
        )

    def test_user_without_advising_data_access(self, app, client, fake_auth):
        """Denies access to a user who cannot access notes and appointments."""
        fake_auth.login(coe_advisor_no_advising_data_uid)
        user = AuthorizedUser.find_by_uid(coe_advisor_no_advising_data_uid)
        assert _api_note_create(
            app=app,
            author_id=user.id,
            body='Diese Aktion ist nicht zulässig.',
            client=client,
            expected_status_code=401,
            sids=[coe_student['sid']],
            subject='Verboten',
        )

    def test_create_note(self, app, client, fake_auth):
        """Create a note."""
        fake_auth.login(coe_advisor_uid)
        subject = 'Vicar in a Tutu'
        new_note = _api_note_create(
            app=app,
            author_id=AuthorizedUser.get_id_per_uid(coe_advisor_uid),
            body='A scanty bit of a thing with a decorative ring',
            client=client,
            sids=[coe_student['sid']],
            subject=subject,
        )
        note_id = new_note.get('id')
        assert new_note['read'] is True
        assert isinstance(note_id, int) and note_id > 0
        assert new_note['author']['uid'] == coe_advisor_uid
        assert 'name' in new_note['author']
        assert new_note['author']['role'] == 'advisor'
        assert new_note['author']['departments'][0]['name'] == 'College of Engineering'
        assert new_note['updatedAt'] is None
        # Get notes per SID and compare
        notes = _get_notes(client, coe_student['uid'])
        match = next((n for n in notes if n['id'] == note_id), None)
        assert match and match['subject'] == subject

    def test_create_private_note(self, app, client, fake_auth):
        """CE3 advisor can create a private note."""
        fake_auth.login(ce3_advisor_uid)
        note = _api_note_create(
            app=app,
            author_id=AuthorizedUser.get_id_per_uid(ce3_advisor_uid),
            body='Somebody went under a dock and there they saw a rock.',
            client=client,
            is_private=True,
            sids=[coe_student['sid']],
            subject='Rock Lobster',
        )
        assert note['isPrivate'] is True
        assert 'rock' in note['body']

    def test_create_note_prefers_ldap_dept_affiliation_and_title(self, app, client, fake_auth):
        fake_auth.login(l_s_major_advisor_uid)
        new_note = _api_note_create(
            app=app,
            author_id=AuthorizedUser.get_id_per_uid(l_s_major_advisor_uid),
            body='Keats and Yeats are on your side',
            client=client,
            sids=[coe_student['sid']],
            subject='A dreaded sunny day',
        )
        assert new_note['author']['departments'][0]['name'] == 'Department of English'
        assert new_note['author']['role'] == 'Harmless Drudge'

    def test_updated_date_is_none_when_note_create(self, app, client, fake_auth):
        """Create a note and expect none updated_at."""
        fake_auth.login(coe_advisor_uid)
        note = _api_note_create(
            app=app,
            client=client,
            author_id=AuthorizedUser.get_id_per_uid(coe_advisor_uid),
            body=None,
            sids=[coe_student['sid']],
            subject='Creating is not updating',
        )
        assert note['createdAt'] is not None
        assert note['updatedAt'] is None

    def test_create_note_with_topics(self, app, client, fake_auth):
        """Create a note with topics."""
        fake_auth.login(coe_advisor_uid)
        note = _api_note_create(
            app=app,
            author_id=AuthorizedUser.get_id_per_uid(coe_advisor_uid),
            body='Facilitate value-added initiatives',
            client=client,
            sids=[coe_student['sid']],
            subject='Incubate transparent web services',
            topics=['Shadrach', 'Meshach', 'Abednego'],
        )
        assert len(note.get('topics')) == 3
        for topic in ('Shadrach', 'Meshach', 'Abednego'):
            assert topic in note.get('topics')
        assert note['createdAt'] is not None
        assert note['updatedAt'] is None

    def test_create_note_with_raw_url_in_body(self, app, client, fake_auth):
        """Create a note with topics."""
        fake_auth.login(coe_advisor_uid)
        note = _api_note_create(
            app=app,
            author_id=AuthorizedUser.get_id_per_uid(coe_advisor_uid),
            body='Get an online degree at send.money.edu university',
            client=client,
            sids=[coe_student['sid']],
            subject='Get rich quick',
        )
        expected_body = 'Get an online degree at <a href="http://send.money.edu" target="_blank">send.money.edu</a> university'
        assert note.get('body') == expected_body
        assert note['createdAt'] is not None
        assert note['updatedAt'] is None

    def test_create_note_with_attachments(self, app, client, fake_auth, mock_note_template):
        """Create a note, with two attachments."""
        fake_auth.login(coe_advisor_uid)
        base_dir = app.config['BASE_DIR']
        note = _api_note_create(
            app=app,
            attachments=[
                f'{base_dir}/fixtures/mock_advising_note_attachment_1.txt',
                f'{base_dir}/fixtures/mock_advising_note_attachment_2.txt',
            ],
            author_id=AuthorizedUser.get_id_per_uid(coe_advisor_uid),
            body='I come correct',
            client=client,
            sids=[coe_student['sid']],
            subject='I come with attachments',
            template_attachment_ids=list(map(lambda a: a.id, mock_note_template.attachments)),
        )
        template_attachment_count = len(mock_note_template.attachments)
        assert template_attachment_count
        expected_attachment_count = template_attachment_count + 2

        assert len(note.get('attachments')) == expected_attachment_count
        assert note['createdAt'] is not None
        assert note['updatedAt'] is None

    def test_create_note_with_contact_type(self, app, client, fake_auth):
        fake_auth.login(coe_advisor_uid)
        note = _api_note_create(
            app=app,
            author_id=AuthorizedUser.get_id_per_uid(coe_advisor_uid),
            body='Do you wanna make tea at the BBC?',
            client=client,
            contact_type='In-person same day',
            sids=[coe_student['sid']],
            subject='Career Opportunities',
        )
        assert note['contactType'] == 'In-person same day'

    def test_invalid_contact_type(self, app, client, fake_auth):
        fake_auth.login(coe_advisor_uid)
        _api_note_create(
            app=app,
            author_id=AuthorizedUser.get_id_per_uid(coe_advisor_uid),
            body='Do you wanna be, do you really wanna be a cop?',
            client=client,
            contact_type='Bope',
            expected_status_code=400,
            sids=[coe_student['sid']],
            subject='Career Opportunities',
        )

    def test_create_note_with_set_date(self, app, client, fake_auth):
        fake_auth.login(coe_advisor_uid)
        note = _api_note_create(
            app=app,
            author_id=AuthorizedUser.get_id_per_uid(coe_advisor_uid),
            body='Career opportunities, the ones that never knock',
            client=client,
            set_date='2021-12-25',
            sids=[coe_student['sid']],
            subject='Career Opportunities',
        )
        assert note['setDate'] == '2021-12-25'

    def test_invalid_set_date(self, app, client, fake_auth):
        fake_auth.login(coe_advisor_uid)
        _api_note_create(
            app=app,
            author_id=AuthorizedUser.get_id_per_uid(coe_advisor_uid),
            body='Every job they offer you is to keep you out the dock',
            client=client,
            expected_status_code=400,
            set_date='Bope',
            sids=[coe_student['sid']],
            subject='Career Opportunities',
        )


class TestBatchNoteCreation:

    sids = [
        '960759268', '856024035', '370048698', '709706581', '518777297', '912902626', '466030628', '695508833',
        '729680066', '534614253', '329221239', '882981218', '734373851', '968319871', '824231751', '904338427',
        '849739234', '310798157', '301806363', '352212185', '3456789012', '5678901234', '11667051', '8901234567',
        '3456789012', '11667051',
    ]

    def test_user_without_advising_data_access(self, app, client, fake_auth):
        """Denies access to a user who cannot access notes and appointments."""
        fake_auth.login(coe_advisor_no_advising_data_uid)
        user = AuthorizedUser.find_by_uid(coe_advisor_no_advising_data_uid)
        _api_batch_note_create(
            app=app,
            author_id=user.id,
            body='Diese Aktion ist nicht zulässig.',
            client=client,
            expected_status_code=401,
            sids=self.sids,
            subject='Verboten',
        )

    def test_batch_note_creation_with_sids(self, app, client, fake_auth, mock_note_template):
        """Batch note creation with list of SIDs."""
        fake_auth.login(coe_advisor_uid)
        base_dir = app.config['BASE_DIR']
        advisor = AuthorizedUser.find_by_uid(coe_advisor_uid)
        subject = f'Elevate Me Later {datetime.now().timestamp()}'

        # Curated group
        curated_group_ids, sids_in_curated_groups = _get_curated_groups_ids_and_sids(advisor)
        # We need at least one curated_group SID that is NOT in the list o' sids above.
        sid_expected_in_curated_group = '7890123456'
        assert sid_expected_in_curated_group in sids_in_curated_groups
        assert sid_expected_in_curated_group not in self.sids
        # Cohort
        cohort_ids, sids_in_cohorts = _get_cohorts_ids_and_sids(advisor)
        # We need at least one cohort SID that is NOT in the list o' sids above.
        expected_sid_in_cohort = '9000000000'
        assert expected_sid_in_cohort not in self.sids
        assert expected_sid_in_cohort in sids_in_cohorts

        # List above has duplicates - verify that it is de-duped.
        distinct_sids = set(self.sids + sids_in_curated_groups + sids_in_cohorts)
        topics = ['Slanted', 'Enchanted']
        _api_batch_note_create(
            app=app,
            attachments=[
                f'{base_dir}/fixtures/mock_advising_note_attachment_1.txt',
                f'{base_dir}/fixtures/mock_advising_note_attachment_2.txt',
            ],
            author_id=advisor.id,
            body='Well you greet the tokens and stamps, beneath the fake oil burnin\' lamps',
            client=client,
            cohort_ids=cohort_ids,
            contact_type='Admin',
            curated_group_ids=curated_group_ids,
            set_date='2022-01-01',
            sids=self.sids,
            subject=subject,
            template_attachment_ids=list(map(lambda a: a.id, mock_note_template.attachments)),
            topics=topics,
        )
        notes = Note.query.filter(Note.subject == subject).all()
        assert len(notes) == len(distinct_sids)
        matching_notes_read = NoteRead.get_notes_read_by_user(viewer_id=advisor.id, note_ids=[str(n.id) for n in notes])
        assert len(notes) == len(matching_notes_read)

        template_attachment_count = len(mock_note_template.attachments)
        assert template_attachment_count
        expected_attachment_count = template_attachment_count + 2

        for sid in distinct_sids:
            note = next((n for n in notes if n.sid == sid), None)
            assert note
            assert note.subject == subject
            assert note.author_uid == advisor.uid
            assert len(note.topics) == 2
            topics = [t.topic for t in note.topics]
            assert 'Slanted' in topics
            assert 'Enchanted' in topics
            assert len(note.attachments) == expected_attachment_count
            assert note.contact_type == 'Admin'
            assert note.set_date == date(2022, 1, 1)


class TestNoteAttachments:

    def test_user_without_advising_data_access(self, app, client, fake_auth):
        """Denies access to a user who cannot access notes and appointments."""
        fake_auth.login(coe_advisor_no_advising_data_uid)
        delete_response = client.delete('/api/notes/1/attachment/1')
        assert delete_response.status_code == 401

        with mock_advising_note_s3_bucket(app):
            base_dir = app.config['BASE_DIR']
            data = {'attachment[0]': open(f'{base_dir}/fixtures/mock_advising_note_attachment_1.txt', 'rb')}
            response = client.post(
                '/api/notes/1/attachments',
                buffered=True,
                content_type='multipart/form-data',
                data=data,
            )
        assert response.status_code == 401

    def test_remove_attachment(self, app, client, fake_auth):
        """Remove an attachment from an existing note."""
        fake_auth.login(coe_advisor_uid)
        base_dir = app.config['BASE_DIR']
        note = _api_note_create(
            app=app,
            attachments=[
                f'{base_dir}/fixtures/mock_advising_note_attachment_1.txt',
                f'{base_dir}/fixtures/mock_advising_note_attachment_2.txt',
            ],
            author_id=AuthorizedUser.get_id_per_uid(coe_advisor_uid),
            body='I come correct',
            client=client,
            sids=[coe_student['sid']],
            subject='I come with attachments',
        )
        assert note['updatedAt'] is None
        # Pause one second to ensure a distinct updatedAt.
        sleep(1)

        note_id = note['id']
        id_to_delete = note['attachments'][0]['id']
        id_to_keep = note['attachments'][1]['id']

        delete_response = client.delete(f'/api/notes/{note_id}/attachment/{id_to_delete}')
        assert delete_response.status_code == 200
        assert len(delete_response.json['attachments']) == 1
        assert delete_response.json['attachments'][0]['id'] == id_to_keep

        notes = _get_notes(client, coe_student['uid'])
        match = next((n for n in notes if n['id'] == note_id), None)
        assert len(match.get('attachments')) == 1
        assert match['attachments'][0]['id'] == id_to_keep
        assert match['updatedAt'] is not None

    def test_add_attachment(self, app, client, fake_auth):
        """Add an attachment to an existing note."""
        fake_auth.login(coe_advisor_uid)
        base_dir = app.config['BASE_DIR']
        note = _api_note_create(
            app=app,
            author_id=AuthorizedUser.get_id_per_uid(coe_advisor_uid),
            body='I travel light',
            client=client,
            sids=[coe_student['sid']],
            subject='No attachments yet',
        )
        assert note['updatedAt'] is None
        # Pause one second to ensure a distinct updatedAt.
        sleep(1)
        note_id = note['id']
        with mock_advising_note_s3_bucket(app):
            data = {'attachment[0]': open(f'{base_dir}/fixtures/mock_advising_note_attachment_1.txt', 'rb')}
            response = client.post(
                f'/api/notes/{note_id}/attachments',
                buffered=True,
                content_type='multipart/form-data',
                data=data,
            )
        assert response.status_code == 200
        updated_note = response.json
        assert len(updated_note['attachments']) == 1
        assert updated_note['attachments'][0]['filename'] == 'mock_advising_note_attachment_1.txt'
        assert updated_note['updatedAt'] is not None

    def test_add_attachments(self, app, client, fake_auth):
        """Add multiple attachments to an existing note."""
        fake_auth.login(coe_advisor_uid)
        base_dir = app.config['BASE_DIR']
        note = _api_note_create(
            app=app,
            author_id=AuthorizedUser.get_id_per_uid(coe_advisor_uid),
            body='I travel light',
            client=client,
            sids=[coe_student['sid']],
            subject='No attachments yet',
        )
        assert note['updatedAt'] is None
        # Pause one second to ensure a distinct updatedAt.
        sleep(1)
        note_id = note['id']
        with mock_advising_note_s3_bucket(app):
            data = {
                'attachment[0]': open(f'{base_dir}/fixtures/mock_advising_note_attachment_1.txt', 'rb'),
                'attachment[1]': open(f'{base_dir}/fixtures/mock_advising_note_attachment_2.txt', 'rb'),
            }
            response = client.post(
                f'/api/notes/{note_id}/attachments',
                buffered=True,
                content_type='multipart/form-data',
                data=data,
            )
        assert response.status_code == 200
        updated_note = response.json
        assert len(updated_note['attachments']) == 2
        assert updated_note['attachments'][0]['filename'] == 'mock_advising_note_attachment_1.txt'
        assert updated_note['attachments'][1]['filename'] == 'mock_advising_note_attachment_2.txt'
        assert updated_note['updatedAt'] is not None


class TestMarkNoteRead:

    def test_mark_read_not_authenticated(self, client):
        """Returns 401 if not authenticated."""
        assert client.post('/api/notes/11667051-00001/mark_read').status_code == 401

    def test_user_without_advising_data_access(self, client, fake_auth):
        """Denies access to a user who cannot access notes and appointments."""
        fake_auth.login(coe_advisor_no_advising_data_uid)
        assert client.post('/api/notes/11667051-00001/mark_read').status_code == 401

    def test_mark_note_read(self, app, client, fake_auth):
        """Marks a note as read."""
        fake_auth.login(coe_advisor_uid)
        all_notes_unread = _get_notes(client, 61889)
        assert len(all_notes_unread) == 12
        for note in all_notes_unread:
            assert note['read'] is False

        # SIS notes
        response = client.post('/api/notes/11667051-00001/mark_read')
        assert response.status_code == 201
        response = client.post('/api/notes/11667051-00003/mark_read')
        assert response.status_code == 201
        # ASC note
        response = client.post('/api/notes/11667051-139379/mark_read')
        assert response.status_code == 201
        # Data Science note
        response = client.post('/api/notes/11667051-20190801112456/mark_read')
        assert response.status_code == 201
        # E&I note
        response = client.post('/api/notes/11667051-151620/mark_read')
        assert response.status_code == 201
        # SIS eForm
        response = client.post('/api/notes/eform-10096/mark_read')
        assert response.status_code == 201

        all_notes_after_read = _get_notes(client, 61889)
        assert len(all_notes_after_read) == 12
        assert all_notes_after_read[0]['id'] == '11667051-00001'
        assert all_notes_after_read[0]['read'] is True
        assert all_notes_after_read[1]['id'] == '11667051-00002'
        assert all_notes_after_read[1]['read'] is False
        assert all_notes_after_read[2]['id'] == '11667051-00003'
        assert all_notes_after_read[2]['read'] is True
        assert all_notes_after_read[3]['id'] == '11667051-00004'
        assert all_notes_after_read[3]['read'] is False
        assert all_notes_after_read[4]['id'] == '11667051-139362'
        assert all_notes_after_read[4]['read'] is False
        assert all_notes_after_read[5]['id'] == '11667051-139379'
        assert all_notes_after_read[5]['read'] is True
        assert all_notes_after_read[6]['id'] == '11667051-20181003051208'
        assert all_notes_after_read[6]['read'] is False
        assert all_notes_after_read[7]['id'] == '11667051-20190801112456'
        assert all_notes_after_read[7]['read'] is True
        assert all_notes_after_read[8]['id'] == '11667051-151620'
        assert all_notes_after_read[8]['read'] is True
        assert all_notes_after_read[9]['id'] == 'eform-101'
        assert all_notes_after_read[9]['read'] is False
        assert all_notes_after_read[10]['id'] == 'eform-10099'
        assert all_notes_after_read[10]['read'] is False
        assert all_notes_after_read[11]['id'] == 'eform-10096'
        assert all_notes_after_read[11]['read'] is True


class TestUpdateNotes:

    @classmethod
    def _api_note_update(
            cls,
            app,
            body,
            client,
            note_id,
            subject,
            expected_status_code=200,
            contact_type=None,
            is_private=False,
            set_date=None,
            topics=(),
    ):
        with mock_advising_note_s3_bucket(app):
            data = {
                'id': note_id,
                'body': body,
                'isPrivate': is_private,
                'subject': subject,
                'topics': ','.join(topics),
            }
            if contact_type:
                data['contactType'] = contact_type
            if set_date:
                data['setDate'] = set_date
            response = client.post(
                '/api/notes/update',
                buffered=True,
                content_type='multipart/form-data',
                data=data,
            )
            assert response.status_code == expected_status_code
            return response.json

    def test_note_update_not_authenticated(self, app, mock_advising_note, client):
        """Returns 401 if not authenticated."""
        self._api_note_update(
            app=app,
            body='Hack the body!',
            client=client,
            expected_status_code=401,
            note_id=mock_advising_note.id,
            subject='Hack the subject!',
        )

    def test_unauthorized_note_privacy_change(self, app, client, fake_auth, mock_advising_note):
        """Returns 401 if unauthorized to update note privacy."""
        fake_auth.login(coe_advisor_uid)
        self._api_note_update(
            app=app,
            body=mock_advising_note.body,
            client=client,
            expected_status_code=403,
            is_private=not mock_advising_note.is_private,
            note_id=mock_advising_note.id,
            subject=mock_advising_note.subject,
        )

    def test_user_without_advising_data_access(self, app, client, fake_auth, mock_coe_advising_note):
        """Denies access to a user who cannot access notes and appointments."""
        fake_auth.login(coe_advisor_no_advising_data_uid)
        assert self._api_note_update(
            app=app,
            body='',
            client=client,
            expected_status_code=401,
            note_id=mock_coe_advising_note.id,
            subject='Change the subject',
        )

    def test_unauthorized_update_note(self, app, client, fake_auth, mock_coe_advising_note):
        """Deny user's attempt to edit someone else's note."""
        original_subject = mock_coe_advising_note.subject
        fake_auth.login(asc_advisor_uid)
        assert self._api_note_update(
            app=app,
            body='Hack someone else\'s body!',
            client=client,
            expected_status_code=403,
            note_id=mock_coe_advising_note.id,
            subject='Hack someone else\'s subject!',
        )
        assert Note.find_by_id(note_id=mock_coe_advising_note.id).subject == original_subject

    def test_update_note_with_raw_url_in_body(self, app, client, fake_auth, mock_coe_advising_note):
        """Updates subject and body of note."""
        fake_auth.login(mock_coe_advising_note.author_uid)
        expected_subject = 'There must have been a plague of them'
        body = '<p>They were <a href="http://www.guzzle.com">www.guzzle.com</a> at <b>https://marsh.mallows.com</b> and <a href="http://www.foxnews.com">FOX news</a></p>'  # noqa: E501
        expected_body = '<p>They were <a href="http://www.guzzle.com">www.guzzle.com</a> at <b><a href="https://marsh.mallows.com" target="_blank">https://marsh.mallows.com</a></b> and <a href="http://www.foxnews.com">FOX news</a></p>'  # noqa: E501
        updated_note_response = self._api_note_update(
            app=app,
            body=body,
            client=client,
            note_id=mock_coe_advising_note.id,
            subject=expected_subject,
        )
        assert updated_note_response['read'] is True
        updated_note = Note.find_by_id(note_id=mock_coe_advising_note.id)
        assert updated_note.subject == expected_subject
        assert updated_note.body == expected_body

    def test_update_note_topics(self, app, client, fake_auth, mock_asc_advising_note):
        """Update note topics."""
        fake_auth.login(mock_asc_advising_note.author_uid)
        expected_topics = ['Blinking lights', ' and other revelations']
        api_json = self._api_note_update(
            app=app,
            body=mock_asc_advising_note.body,
            client=client,
            note_id=mock_asc_advising_note.id,
            subject=mock_asc_advising_note.subject,
            topics=expected_topics,
        )
        assert api_json['read'] is True
        assert len(api_json['topics']) == 2
        assert 'Blinking lights' in api_json['topics']
        assert ' and other revelations' in api_json['topics']

    def test_remove_note_topics(self, app, client, fake_auth, mock_asc_advising_note):
        """Delete note topics."""
        fake_auth.login(mock_asc_advising_note.author_uid)
        original_topics = mock_asc_advising_note.topics
        assert len(original_topics)
        api_json = self._api_note_update(
            app=app,
            body=mock_asc_advising_note.body,
            client=client,
            note_id=mock_asc_advising_note.id,
            subject=mock_asc_advising_note.subject,
            topics=[],
        )
        assert not api_json['topics']
        # Put those topics back
        api_json = self._api_note_update(
            app=app,
            body=mock_asc_advising_note.body,
            client=client,
            note_id=mock_asc_advising_note.id,
            subject=mock_asc_advising_note.subject,
            topics=[t.topic for t in original_topics],
        )
        assert set(api_json['topics']) == set([t.topic for t in original_topics])

    def test_update_note_contact_type(self, app, client, fake_auth, mock_asc_advising_note):
        """Update note contact type."""
        fake_auth.login(mock_asc_advising_note.author_uid)
        api_json = self._api_note_update(
            app=app,
            body=mock_asc_advising_note.body,
            client=client,
            note_id=mock_asc_advising_note.id,
            subject=mock_asc_advising_note.subject,
            contact_type='Online same day',
        )
        assert api_json['read'] is True
        assert api_json['contactType'] == 'Online same day'

    def test_update_note_set_date(self, app, client, fake_auth, mock_asc_advising_note):
        """Update note set date."""
        fake_auth.login(mock_asc_advising_note.author_uid)
        api_json = self._api_note_update(
            app=app,
            body=mock_asc_advising_note.body,
            client=client,
            note_id=mock_asc_advising_note.id,
            subject=mock_asc_advising_note.subject,
            set_date='2021-10-31',
        )
        assert api_json['read'] is True
        assert api_json['setDate'] == '2021-10-31'


class TestDeleteNote:
    """Delete note API."""

    def test_not_authenticated(self, client):
        """You must log in to delete a note."""
        response = client.delete('/api/notes/delete/123')
        assert response.status_code == 401

    def test_user_without_advising_data_access(self, client, fake_auth, mock_coe_advising_note):
        """Denies access to a user who cannot access notes and appointments."""
        fake_auth.login(coe_advisor_no_advising_data_uid)
        response = client.delete(f'/api/notes/delete/{mock_coe_advising_note.id}')
        assert response.status_code == 401
        assert Note.find_by_id(mock_coe_advising_note.id)

    def test_unauthorized(self, client, fake_auth, mock_coe_advising_note):
        """Advisor cannot delete the note of another."""
        fake_auth.login('6446')
        response = client.delete(f'/api/notes/delete/{mock_coe_advising_note.id}')
        assert response.status_code == 403
        assert Note.find_by_id(mock_coe_advising_note.id)

    def test_advisor_cannot_delete(self, client, fake_auth, mock_coe_advising_note):
        """Advisor cannot delete her own note."""
        fake_auth.login(mock_coe_advising_note.author_uid)
        response = client.delete(f'/api/notes/delete/{mock_coe_advising_note.id}')
        assert response.status_code == 403
        assert Note.find_by_id(mock_coe_advising_note.id)

    def test_admin_delete(self, client, fake_auth, mock_coe_advising_note):
        """Admin can delete another user's note."""
        original_count_per_sid = len(Note.get_notes_by_sid(mock_coe_advising_note.sid))
        fake_auth.login(admin_uid)
        note_id = mock_coe_advising_note.id
        response = client.delete(f'/api/notes/delete/{note_id}')
        assert response.status_code == 200
        assert not Note.find_by_id(note_id)
        assert 1 == original_count_per_sid - len(Note.get_notes_by_sid(mock_coe_advising_note.sid))
        assert not Note.update(note_id=note_id, subject='Deleted note cannot be updated')

    def test_delete_note_with_topics(self, app, client, fake_auth):
        """Delete a note with topics."""
        fake_auth.login(coe_advisor_uid)
        note = _api_note_create(
            app=app,
            author_id=AuthorizedUser.get_id_per_uid(coe_advisor_uid),
            body='Conveniently repurpose enterprise-wide action items',
            client=client,
            sids=[coe_student['sid']],
            subject='Recontextualize open-source supply-chains',
            topics=['strategic interfaces'],
        )
        # Log in as Admin and delete the note
        fake_auth.login(admin_uid)
        note_id = note.get('id')
        response = client.delete(f'/api/notes/delete/{note_id}')
        assert response.status_code == 200
        # TODO: add deleted_at column to NoteTopic and populate it when parent Note is deleted.
        # assert not NoteTopic.find_by_note_id(note_id)

    def test_delete_note_with_attachments(self, app, client, fake_auth):
        """Delete a note with two attachments."""
        fake_auth.login(coe_advisor_uid)
        base_dir = app.config['BASE_DIR']
        note = _api_note_create(
            app=app,
            attachments=[
                f'{base_dir}/fixtures/mock_advising_note_attachment_1.txt',
                f'{base_dir}/fixtures/mock_advising_note_attachment_2.txt',
            ],
            author_id=AuthorizedUser.get_id_per_uid(coe_advisor_uid),
            body='Then my little dog Lassie, she sailed off to the moon',
            client=client,
            sids=[coe_student['sid']],
            subject='My little dog Lassie packed her bags and went out on to the porch',
        )
        attachment_ids = [a['id'] for a in note.get('attachments')]
        assert len(attachment_ids) == 2
        assert NoteAttachment.find_by_id(attachment_ids[0]) and NoteAttachment.find_by_id(attachment_ids[1])

        # Log in as Admin and delete the note
        fake_auth.login(admin_uid)
        note_id = note['id']
        response = client.delete(f'/api/notes/delete/{note_id}')
        assert response.status_code == 200
        assert not NoteAttachment.find_by_id(attachment_ids[0])
        assert not NoteAttachment.find_by_id(attachment_ids[1])


class TestStreamNoteAttachments:

    def test_not_authenticated(self, client):
        """Returns 401 if not authenticated."""
        assert client.get('/api/notes/attachment/9000000000_00002_1.pdf').status_code == 401

    def test_user_without_advising_data_access(self, app, client, fake_auth):
        """Denies access to a user who cannot access notes and appointments."""
        with mock_legacy_note_attachment(app):
            fake_auth.login(coe_advisor_no_advising_data_uid)
            assert client.get('/api/notes/attachment/9000000000_00002_1.pdf').status_code == 401

    def test_unauthorized_request_for_private_note(self, app, client, mock_private_advising_note, fake_auth):
        """Denies access to a user who cannot access notes and appointments."""
        fake_auth.login(coe_advisor_uid)
        attachments = mock_private_advising_note.attachments
        assert attachments
        assert client.get(f'/api/notes/attachment/{attachments[0].id}').status_code == 403

    def test_authorized_request_for_private_note(self, app, client, mock_private_advising_note, fake_auth):
        """Denies access to a user who cannot access notes and appointments."""
        fake_auth.login(ce3_advisor_uid)
        attachments = mock_private_advising_note.attachments
        assert attachments
        assert client.get(f'/api/notes/attachment/{attachments[0].id}').status_code == 200

    def test_stream_attachment(self, app, client, fake_auth):
        with mock_legacy_note_attachment(app):
            fake_auth.login(coe_advisor_uid)
            response = client.get('/api/notes/attachment/9000000000_00002_1.pdf')
            assert response.status_code == 200
            assert response.headers['Content-Type'] == 'application/octet-stream'
            assert response.headers['Content-Disposition'] == "attachment; filename*=UTF-8''dog_eaten_homework.pdf"
            assert response.data == b'When in the course of human events, it becomes necessarf arf woof woof woof'

    def test_stream_attachment_reports_missing_files_not_found(self, app, client, fake_auth):
        with mock_legacy_note_attachment(app):
            fake_auth.login(asc_advisor_uid)
            response = client.get('/api/notes/attachment/h0ax.lol')
            assert response.status_code == 404
            assert response.data == b'Sorry, attachment not available.'


class TestStreamNotesZip:

    def test_not_authenticated(self, client):
        """Returns 401 if not authenticated."""
        assert client.get('/api/notes/download_for_sid/9000000000').status_code == 401

    def test_not_authorized(self, client, fake_auth):
        """Returns 401 if not admin or director."""
        fake_auth.login(coe_advisor_uid)
        assert client.get('/api/notes/download_for_sid/9000000000').status_code == 401

    def test_director_without_advising_data_access(self, client, fake_auth):
        """Denies access to a director who cannot access notes and appointments."""
        fake_auth.login(l_s_director_no_advising_data_uid)
        assert client.get('/api/notes/download_for_sid/9000000000').status_code == 401

    def test_not_found(self, client, fake_auth):
        """Returns 404 if SID not found."""
        fake_auth.login(admin_uid)
        assert client.get('/api/notes/download_for_sid/9999999999').status_code == 404

    def _assert_zip_download(self, app, client):
        today = localize_datetime(utc_now()).strftime('%Y%m%d')
        with mock_legacy_note_attachment(app):
            response = client.get('/api/notes/download_for_sid/9000000000')
            assert response.status_code == 200
            assert response.headers['Content-Type'] == 'application/zip'
            assert response.headers['Content-Disposition'] == f'attachment; filename=advising_notes_wolfgang_pauli-o%27rourke_{today}.zip'
            assert response.data

    def test_authorizes_director(self, app, client, fake_auth):
        fake_auth.login(l_s_director_uid)
        self._assert_zip_download(app, client)

    def test_authorizes_admin(self, app, client, fake_auth):
        fake_auth.login(admin_uid)
        self._assert_zip_download(app, client)


def _get_notes(client, uid):
    response = client.get(f'/api/student/by_uid/{uid}')
    assert response.status_code == 200
    return response.json['notifications']['note']


def _asc_note_with_attachment():
    for note in Note.get_notes_by_sid('11667051'):
        if len(note.attachments):
            return note
    return None


def _api_note_create(
        app,
        author_id,
        body,
        client,
        sids,
        subject,
        attachments=(),
        expected_status_code=200,
        contact_type=None,
        is_private=False,
        set_date=None,
        template_attachment_ids=(),
        topics=(),
):
    with mock_advising_note_s3_bucket(app):
        data = {
            'authorId': author_id,
            'body': body,
            'isPrivate': is_private,
            'sids': sids,
            'subject': subject,
            'templateAttachmentIds': ','.join(str(_id) for _id in template_attachment_ids),
            'topics': ','.join(topics),
        }
        if contact_type:
            data['contactType'] = contact_type
        if set_date:
            data['setDate'] = set_date
        for index, path in enumerate(attachments):
            data[f'attachment[{index}]'] = open(path, 'rb')
        response = client.post(
            '/api/notes/create',
            buffered=True,
            content_type='multipart/form-data',
            data=data,
        )
        assert response.status_code == expected_status_code
        return response.json


def _api_batch_note_create(
        app,
        author_id,
        body,
        client,
        subject,
        attachments=(),
        cohort_ids=None,
        curated_group_ids=None,
        expected_status_code=200,
        contact_type=None,
        is_private=False,
        set_date=None,
        sids=None,
        template_attachment_ids=(),
        topics=(),
):
    with mock_advising_note_s3_bucket(app):
        data = {
            'authorId': author_id,
            'body': body,
            'cohortIds': cohort_ids or [],
            'curatedGroupIds': curated_group_ids or [],
            'isBatchMode': sids and len(sids) > 1,
            'isPrivate': is_private,
            'sids': sids or [],
            'subject': subject,
            'templateAttachmentIds': template_attachment_ids or [],
            'topics': ','.join(topics),
        }
        for index, path in enumerate(attachments):
            data[f'attachment[{index}]'] = open(path, 'rb')
        if contact_type:
            data['contactType'] = contact_type
        if set_date:
            data['setDate'] = set_date
        response = client.post(
            '/api/notes/create',
            buffered=True,
            content_type='multipart/form-data',
            data=data,
        )
        assert response.status_code == expected_status_code


def _get_curated_groups_ids_and_sids(advisor):
    sids = []
    curated_group_ids = []
    for curated_group in CuratedGroup.get_curated_groups(advisor.id):
        curated_group_ids.append(curated_group.id)
        sids = sids + CuratedGroup.get_all_sids(curated_group.id)
    return curated_group_ids, sids


def _get_cohorts_ids_and_sids(advisor):
    cohort_ids = [c['id'] for c in all_cohorts_owned_by(advisor.uid)]
    sids = []
    for cohort_id in cohort_ids:
        sids = sids + CohortFilter.get_sids(cohort_id)
    return cohort_ids, sids
