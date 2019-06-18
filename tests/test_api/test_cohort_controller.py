"""
Copyright ©2019. The Regents of the University of California (Regents). All Rights Reserved.

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

from boac.models.cohort_filter import CohortFilter
import pytest
import simplejson as json
from tests.test_api.api_test_utils import all_cohorts_owned_by

admin_uid = '2040'
asc_advisor_uid = '1081940'
coe_advisor_uid = '1133399'


@pytest.fixture()
def admin_session(fake_auth):
    fake_auth.login(admin_uid)


@pytest.fixture()
def asc_advisor_session(fake_auth):
    fake_auth.login(asc_advisor_uid)


@pytest.fixture()
def coe_advisor_session(fake_auth):
    fake_auth.login(coe_advisor_uid)


@pytest.fixture()
def asc_owned_cohort():
    cohorts = all_cohorts_owned_by(asc_advisor_uid)
    return next((c for c in cohorts if c['name'] == 'All sports'), None)


@pytest.fixture()
def coe_owned_cohort():
    cohorts = all_cohorts_owned_by(coe_advisor_uid)
    return next((c for c in cohorts if c['name'] == 'Radioactive Women and Men'), None)


class TestCohortDetail:
    """Cohort API."""

    def test_my_cohorts_not_authenticated(self, client):
        """Rejects anonymous user."""
        response = client.get('/api/cohorts/my')
        assert response.status_code == 401

    def test_my_cohorts(self, coe_advisor_session, client):
        """Returns user's cohorts."""
        response = client.get('/api/cohorts/my')
        assert response.status_code == 200
        cohorts = response.json
        assert len(cohorts) == 2
        for key in 'name', 'alertCount', 'criteria', 'totalStudentCount', 'isOwnedByCurrentUser':
            assert key in cohorts[0], f'Missing cohort element: {key}'

    def test_students_with_alert_counts(self, asc_advisor_session, client, create_alerts, db_session):
        """Pre-load students into cache for consistent alert data."""
        from boac.models.alert import Alert

        assert client.get('/api/student/61889').status_code == 200
        assert client.get('/api/student/98765').status_code == 200

        Alert.update_all_for_term(2178)
        cohorts = all_cohorts_owned_by(asc_advisor_uid)
        assert len(cohorts)
        cohort_id = cohorts[0]['id']
        response = client.get(f'/api/cohort/{cohort_id}/students_with_alerts')
        assert response.status_code == 200
        students_with_alerts = response.json
        assert len(students_with_alerts) == 3

        deborah = students_with_alerts[0]
        assert deborah['sid'] == '11667051'
        assert deborah['alertCount'] == 3
        # Summary student data is included with alert counts, but full term feeds are not.
        assert deborah['cumulativeGPA'] == 3.8
        assert deborah['cumulativeUnits'] == 101.3
        assert deborah['expectedGraduationTerm']['name'] == 'Fall 2019'
        assert deborah['level'] == 'Junior'
        assert len(deborah['majors']) == 2
        assert deborah['term']['enrolledUnits'] == 12.5
        assert deborah['termGpa'][0]['gpa'] == 2.9
        assert 'enrollments' not in deborah['term']

        dave_doolittle = students_with_alerts[1]
        assert dave_doolittle['sid'] == '2345678901'
        assert dave_doolittle['uid']
        assert dave_doolittle['firstName']
        assert dave_doolittle['lastName']
        assert dave_doolittle['alertCount'] == 1

        def _get_alerts(uid):
            response = client.get(f'/api/student/{uid}')
            assert response.status_code == 200
            return response.json['notifications']['alert']

        alert_to_dismiss = _get_alerts(61889)[0]['id']
        client.get('/api/alerts/' + str(alert_to_dismiss) + '/dismiss')
        alert_to_dismiss = _get_alerts(98765)[0]['id']
        client.get('/api/alerts/' + str(alert_to_dismiss) + '/dismiss')

        students_with_alerts = client.get(f'/api/cohort/{cohort_id}/students_with_alerts').json
        assert len(students_with_alerts) == 2
        assert students_with_alerts[0]['sid'] == '11667051'
        assert students_with_alerts[0]['alertCount'] == 2

    def test_cohorts_all(self, asc_advisor_session, client):
        """Returns all cohorts per owner."""
        response = client.get('/api/cohorts/all')
        assert response.status_code == 200
        api_json = response.json
        count = len(api_json)
        assert count == 2
        for index, entry in enumerate(api_json):
            user = entry['user']
            if 0 < index < count:
                # Verify order
                assert user['name'] > api_json[index - 1]['user']['name']
            assert 'uid' in user
            cohorts = entry['cohorts']
            cohort_count = len(cohorts)
            for c_index, cohort in enumerate(cohorts):
                if 0 < c_index < cohort_count:
                    # Verify order
                    assert cohort['name'] > cohorts[c_index - 1]['name']
                assert 'id' in cohort

    def test_get_cohort(self, coe_advisor_session, client, coe_owned_cohort, create_alerts):
        """Returns a well-formed response with filtered cohort and alert count per student."""
        cohort_id = coe_owned_cohort['id']
        response = client.get(f'/api/cohort/{cohort_id}')
        assert response.status_code == 200
        cohort = json.loads(response.data)
        assert cohort['id'] == cohort_id
        assert cohort['name'] == coe_owned_cohort['name']
        assert 'students' in cohort
        assert cohort['students'][0].get('alertCount') == 3

    def test_get_cohort_without_students(self, coe_advisor_session, client, coe_owned_cohort):
        """Returns a well-formed response with cohort and no students."""
        cohort_id = coe_owned_cohort['id']
        response = client.get(f'/api/cohort/{cohort_id}?includeStudents=false')
        assert response.status_code == 200
        cohort = json.loads(response.data)
        assert 'students' not in cohort

    def test_unauthorized_get_cohort(self, asc_advisor_session, client, coe_owned_cohort):
        """Returns a well-formed response with custom cohort."""
        cohort_id = coe_owned_cohort['id']
        response = client.get(f'/api/cohort/{cohort_id}')
        assert response.status_code == 404
        assert 'No cohort found' in json.loads(response.data)['message']

    def test_undeclared_major(self, asc_advisor_session, client):
        """Returns a well-formed response with custom cohort."""
        cohort = all_cohorts_owned_by(asc_advisor_uid)[-1]
        cohort_id = cohort['id']
        response = client.get(f'/api/cohort/{cohort_id}')
        assert response.status_code == 200
        cohort = json.loads(response.data)
        assert cohort['name'] == 'Undeclared students'
        students = cohort['students']
        assert cohort['totalStudentCount'] == len(students) == 1
        # We expect the student with 'Letters & Sci Undeclared UG' major
        assert students[0]['sid'] == '5678901234'

    def test_includes_cohort_member_sis_data(self, asc_advisor_session, asc_owned_cohort, client):
        """Includes SIS data for custom cohort students."""
        cohort_id = asc_owned_cohort['id']
        response = client.get(f'/api/cohort/{cohort_id}')
        assert response.status_code == 200
        athlete = next(m for m in response.json['students'] if m['firstName'] == 'Deborah')
        assert athlete['cumulativeGPA'] == 3.8
        assert athlete['cumulativeUnits'] == 101.3
        assert athlete['level'] == 'Junior'
        assert athlete['majors'] == ['English BA', 'Nuclear Engineering BS']

    def test_includes_cohort_member_current_enrollments(self, asc_advisor_session, asc_owned_cohort, client):
        """Includes current-term active enrollments for custom cohort students."""
        cohort_id = asc_owned_cohort['id']
        response = client.get(f'/api/cohort/{cohort_id}?orderBy=firstName')
        assert response.status_code == 200
        athlete = next(m for m in response.json['students'] if m['firstName'] == 'Deborah')

        term = athlete['term']
        assert term['termName'] == 'Fall 2017'
        assert term['enrolledUnits'] == 12.5
        assert len(term['enrollments']) == 5
        assert term['enrollments'][0]['displayName'] == 'BURMESE 1A'
        assert len(term['enrollments'][0]['canvasSites']) == 1

    def test_includes_cohort_member_term_gpa(self, asc_advisor_session, asc_owned_cohort, client):
        cohort_id = asc_owned_cohort['id']
        response = client.get(f'/api/cohort/{cohort_id}?orderBy=firstName')
        deborah = next(m for m in response.json['students'] if m['firstName'] == 'Deborah')
        assert len(deborah['termGpa']) == 4
        assert deborah['termGpa'][0] == {'termName': 'Spring 2018', 'gpa': 2.9}
        assert deborah['termGpa'][3] == {'termName': 'Spring 2016', 'gpa': 3.8}

    def test_includes_cohort_member_athletics_asc(self, asc_advisor_session, asc_owned_cohort, client):
        """Includes athletic data custom cohort members for ASC advisors."""
        cohort_id = asc_owned_cohort['id']
        response = client.get(f'/api/cohort/{cohort_id}')
        athlete = next(m for m in response.json['students'] if m['firstName'] == 'Deborah')
        assert len(athlete['athleticsProfile']['athletics']) == 2
        assert athlete['athleticsProfile']['inIntensiveCohort'] is not None
        assert athlete['athleticsProfile']['isActiveAsc'] is not None
        assert athlete['athleticsProfile']['statusAsc'] is not None
        tennis = next(membership for membership in athlete['athleticsProfile']['athletics'] if membership['groupCode'] == 'WTE')
        field_hockey = next(membership for membership in athlete['athleticsProfile']['athletics'] if membership['groupCode'] == 'WFH')
        assert tennis['groupName'] == 'Women\'s Tennis'
        assert tennis['teamCode'] == 'TNW'
        assert tennis['teamName'] == 'Women\'s Tennis'
        assert field_hockey['groupName'] == 'Women\'s Field Hockey'
        assert field_hockey['teamCode'] == 'FHW'
        assert field_hockey['teamName'] == 'Women\'s Field Hockey'

    def test_omits_cohort_member_athletics_non_asc(self, coe_advisor_session, client, coe_owned_cohort):
        """Omits athletic data for non-ASC advisors."""
        cohort_id = coe_owned_cohort['id']
        response = client.get(f'/api/cohort/{cohort_id}')
        secretly_an_athlete = next(m for m in response.json['students'] if m['firstName'] == 'Deborah')
        assert 'athletics' not in secretly_an_athlete
        assert 'inIntensiveCohort' not in secretly_an_athlete
        assert 'isActiveAsc' not in secretly_an_athlete
        assert 'statusAsc' not in secretly_an_athlete

    def test_includes_cohort_member_athletics_advisors(self, admin_session, client, coe_owned_cohort):
        """Includes athletic data for admins."""
        cohort_id = coe_owned_cohort['id']
        response = client.get(f'/api/cohort/{cohort_id}')
        athlete = next(m for m in response.json['students'] if m['firstName'] == 'Deborah')
        assert len(athlete['athleticsProfile']['athletics']) == 2
        assert athlete['athleticsProfile']['inIntensiveCohort'] is not None
        assert athlete['athleticsProfile']['isActiveAsc'] is not None
        assert athlete['athleticsProfile']['statusAsc'] is not None

    def test_get_cohort_404(self, client, coe_advisor_session):
        """Returns a well-formed response when no cohort found."""
        response = client.get('/api/cohort/99999999')
        assert response.status_code == 404
        assert 'No cohort found' in str(response.data)

    def test_offset_and_limit(self, asc_advisor_session, asc_owned_cohort, client):
        """Returns a well-formed response with custom cohort."""
        cohort_id = asc_owned_cohort['id']
        api_path = f'/api/cohort/{cohort_id}'
        # First, offset is zero
        response = client.get(f'{api_path}?offset={0}&limit={1}')
        data_0 = json.loads(response.data)
        assert data_0['totalStudentCount'] == 4
        assert len(data_0['students']) == 1
        # Now, offset is one
        response = client.get(f'{api_path}?offset={1}&limit={1}')
        data_1 = json.loads(response.data)
        assert len(data_1['students']) == 1
        # Verify that a different offset results in a different member
        assert data_0['students'][0]['uid'] != data_1['students'][0]['uid']

    def test_unauthorized_request_for_athletic_study_center_data(self, client, fake_auth):
        """In order to access intensive_cohort, inactive status, etc. the user must be either ASC or Admin."""
        fake_auth.login('1022796')
        data = {
            'name': 'My filtered cohort just hacked the system!',
            'isInactiveAsc': True,
        }
        response = client.post('/api/cohort/create', data=json.dumps(data), content_type='application/json')
        assert response.status_code == 403


class TestCohortCreate:
    """Cohort Create API."""

    @classmethod
    def _post_cohort_create(cls, client, json_data=(), expected_status_code=200):
        response = client.post(
            '/api/cohort/create',
            data=json.dumps(json_data),
            content_type='application/json',
        )
        assert response.status_code == expected_status_code
        return json.loads(response.data)

    @staticmethod
    def _api_cohort(client, cohort_id, expected_status_code=200):
        response = client.get(f'/api/cohort/{cohort_id}')
        assert response.status_code == expected_status_code
        return response.json

    @classmethod
    def _assert_create_tennis_cohort(cls, client, data):
        api_json = cls._post_cohort_create(client, data)
        assert 'students' in api_json
        assert api_json['alertCount'] is not None
        assert 'name' in api_json and api_json['name'] == data['name']
        assert 'teamGroups' in api_json
        assert ['MTE', 'WTE'] == [g['groupCode'] for g in api_json['teamGroups']]

        api_json = cls._api_cohort(client, api_json['id'])
        assert 'students' in api_json
        assert api_json['name'] == data['name']
        assert 'teamGroups' in api_json and len(api_json['teamGroups']) == 2
        assert ['MTE', 'WTE'] == [g['groupCode'] for g in api_json['teamGroups']]
        criteria = api_json['criteria']
        assert 'majors' in criteria and len(criteria['majors']) == 2

    @classmethod
    def _assert_create_complex_cohort(cls, client, data):
        api_json = cls._post_cohort_create(client, data)
        cohort_id = api_json['id']
        api_json = cls._api_cohort(client, cohort_id)
        assert 'criteria' in api_json
        assert api_json['alertCount'] is not None
        return api_json

    def test_create_tennis_cohort(self, client, asc_advisor_session):
        """Creates custom cohort, owned by current user."""
        self._assert_create_tennis_cohort(
            client,
            {
                'name': 'Tennis',
                'filters': [
                    {'key': 'groupCodes', 'type': 'array', 'value': 'WTE'},
                    {'key': 'majors', 'type': 'array', 'value': 'Anthropology BA'},
                    {'key': 'groupCodes', 'type': 'array', 'value': 'MTE'},
                    {'key': 'majors', 'type': 'array', 'value': 'Bioengineering BS'},
                ],
            },
        )

    def test_deprecated_create_tennis_cohort(self, client, asc_advisor_session):
        """Creates custom cohort, owned by current user."""
        self._assert_create_tennis_cohort(
            client,
            {
                'name': 'Tennis',
                'groupCodes': ['MTE', 'WTE'],
                'majors': [
                    'Anthropology BA',
                    'Bioengineering BS',
                ],
            },
        )

    def test_deprecated_asc_advisor_is_forbidden(self, asc_advisor_session, client, fake_auth):
        data = {
            'name': 'ASC advisor wants to see students of COE advisor',
            'advisorLdapUids': '1133399',
        }
        assert self._post_cohort_create(client, data, expected_status_code=403)

    def test_asc_advisor_is_forbidden(self, asc_advisor_session, client, fake_auth):
        data = {
            'name': 'ASC advisor wants to see students of COE advisor',
            'filters': [
                {'key': 'advisorLdapUids', 'type': 'array', 'value': '1133399'},
            ],
        }
        assert self._post_cohort_create(client, data, expected_status_code=403)

    def test_admin_create_of_coe_uid_cohort(self, admin_session, client, fake_auth):
        data = {
            'name': 'Admin wants to see students of COE advisor',
            'advisorLdapUids': '1133399',
        }
        api_json = self._post_cohort_create(client, data)
        assert len(api_json['students']) == 2

    def test_cohorts_respect_creators(self, client, fake_auth):
        """Even under an admin view, cohorts constrain their membership by who created them."""
        def _create_cohort(uid):
            fake_auth.login(uid)
            return self._post_cohort_create(
                client,
                {
                    'name': 'Sophomores',
                    'filters': [
                        {'key': 'levels', 'type': 'array', 'value': 'Sophomore'},
                    ],
                },
            )
        asc_cohort_id = _create_cohort(asc_advisor_uid)['id']
        coe_cohort_id = _create_cohort(coe_advisor_uid)['id']
        admin_cohort_id = _create_cohort(admin_uid)['id']

        def _count_students(cohort_id):
            api_json = self._api_cohort(client, cohort_id)
            return len(api_json['students'])

        assert _count_students(asc_cohort_id) == 1
        assert _count_students(coe_cohort_id) == 2
        assert _count_students(admin_cohort_id) == 3

    def test_create_complex_cohort(self, client, coe_advisor_session):
        """Creates custom cohort, with many non-empty filter_criteria."""
        data = {
            'name': 'Complex',
            'filters': [
                {'key': 'majors', 'type': 'array', 'value': 'Gender and Women''s Studies'},
                {'key': 'gpaRanges', 'type': 'array', 'value': 'numrange(2, 2.5, \'[)\')'},
                {'key': 'levels', 'type': 'array', 'value': 'Junior'},
                {'key': 'gpaRanges', 'type': 'array', 'value': 'numrange(0, 2, \'[)\')'},
                {'key': 'majors', 'type': 'array', 'value': 'Environmental Economics & Policy'},
            ],
        }
        api_json = self._assert_create_complex_cohort(client, data)
        for key in api_json['criteria']:
            value = api_json['criteria'][key]
            if key == 'majors':
                assert len(value) == 2
                assert 'Gender and Women''s Studies' in value
            elif key == 'levels':
                assert value == ['Junior']
            elif key == 'gpaRanges':
                assert len(value) == 2
                assert 'numrange(0, 2, \'[)\')' in value
            else:
                assert value is None

    def test_deprecated_create_complex_cohort(self, client, coe_advisor_session):
        """Creates custom cohort, with many non-empty filter_criteria."""
        data = {
            'name': 'Complex',
            'gpaRanges': ['numrange(0, 2, \'[)\')', 'numrange(2, 2.5, \'[)\')'],
            'levels': ['Junior'],
            'majors': [
                'Environmental Economics & Policy',
                'Gender and Women''s Studies',
            ],
        }
        cohort = self._assert_create_complex_cohort(client, data)
        for key in cohort['criteria']:
            assert data.get(key) == cohort['criteria'][key]

    def test_admin_creation_of_asc_cohort(self, client, admin_session):
        """COE advisor cannot use ASC criteria."""
        self._post_cohort_create(
            client,
            {
                'name': 'Admin superpowers',
                'groupCodes': ['MTE', 'WWP'],
            },
        )

    def test_forbidden_cohort_creation(self, client, coe_advisor_session):
        """COE advisor cannot use ASC criteria."""
        data = {'name': 'Sorry Charlie', 'groupCodes': ['MTE', 'WWP']}
        self._post_cohort_create(client, data, expected_status_code=403)


class TestCohortUpdate:
    """Cohort Update API."""

    @classmethod
    def _post_cohort_update(cls, client, json_data=()):
        return client.post(
            '/api/cohort/update',
            data=json.dumps(json_data),
            content_type='application/json',
        )

    def test_unauthorized_cohort_update(self, client, coe_advisor_session):
        cohort = CohortFilter.create(
            uid=asc_advisor_uid,
            name='Swimming, Men\'s',
            filter_criteria={
                'groupCodes': ['MSW', 'MSW-DV', 'MSW-SW'],
            },
        )
        data = {
            'id': cohort['id'],
            'name': 'Hack the name!',
        }
        response = self._post_cohort_update(client, data)
        assert 403 == response.status_code

    def test_update_filters(self, client, asc_advisor_session):
        cohort = CohortFilter.create(
            uid=asc_advisor_uid,
            name='Swimming, Men\'s',
            filter_criteria={
                'groupCodes': ['MSW', 'MSW-DV', 'MSW-SW'],
            },
        )
        # First, we POST an empty name
        cohort_id = cohort['id']
        response = self._post_cohort_update(client, {'id': cohort_id})
        assert 400 == response.status_code
        # Now, we POST a valid name
        data = {
            'id': cohort_id,
            'filters': [
                {'key': 'majors', 'type': 'array', 'value': 'Gender and Women''s Studies'},
                {'key': 'gpaRanges', 'type': 'array', 'value': 'numrange(2, 2.5, \'[)\')'},
            ],
        }
        response = self._post_cohort_update(client, data)
        assert 200 == response.status_code
        updated_cohort = response.json
        assert updated_cohort['alertCount'] is not None
        assert updated_cohort['criteria']['majors'] == ['Gender and Women''s Studies']
        assert updated_cohort['criteria']['gpaRanges'] == ['numrange(2, 2.5, \'[)\')']
        assert updated_cohort['criteria']['groupCodes'] is None

        def remove_empties(criteria):
            return {k: v for k, v in criteria.items() if v is not None}
        cohort = CohortFilter.find_by_id(cohort_id)
        expected = remove_empties(cohort['criteria'])
        actual = remove_empties(updated_cohort['criteria'])
        assert expected == actual

    def test_cohort_update_filter_criteria(self, client, asc_advisor_session):
        name = 'Swimming, Men\'s'
        cohort = CohortFilter.create(
            uid=asc_advisor_uid,
            name=name,
            filter_criteria={
                'groupCodes': ['MBB'],
            },
        )
        cohort_id = cohort['id']
        response = client.get(f'/api/cohort/{cohort_id}')
        cohort = json.loads(response.data)
        assert cohort['totalStudentCount'] == 1
        # Update the db
        updates = {
            'id': cohort_id,
            'criteria': {
                'groupCodes': ['MBB', 'MBB-AA'],
            },
        }
        response = self._post_cohort_update(client, updates)
        assert response.status_code == 200
        # Verify the value of 'student_count' in db
        updated_cohort = CohortFilter.find_by_id(cohort_id)
        assert updated_cohort['totalStudentCount'] == 2
        assert 'sids' not in updated_cohort
        assert updated_cohort['criteria']['groupCodes'] == updates['criteria']['groupCodes']


class TestCohortDelete:
    """Cohort Delete API."""

    def test_delete_cohort_not_authenticated(self, client):
        """Custom cohort deletion requires authentication."""
        response = client.delete('/api/cohort/delete/123')
        assert response.status_code == 401

    def test_delete_cohort_wrong_user(self, client, fake_auth):
        """Custom cohort deletion is only available to owners."""
        cohort = CohortFilter.create(
            uid=coe_advisor_uid,
            name='Badminton teams',
            filter_criteria={
                'groupCodes': ['WWP', 'MWP'],
            },
        )
        assert cohort

        # This user does not own the custom cohort above
        fake_auth.login('2040')
        cohort_id = cohort['id']
        response = client.get(f'/api/cohort/{cohort_id}')
        assert response.status_code == 200
        _cohort = json.loads(response.data)
        assert _cohort['isOwnedByCurrentUser'] is False

        response = client.delete(f'/api/cohort/delete/{cohort_id}')
        assert response.status_code == 400
        assert '2040 does not own' in str(response.data)

    def test_delete_cohort(self, client, coe_advisor_session):
        """Deletes existing custom cohort while enforcing rules of ownership."""
        name = 'Water polo teams'
        cohort = CohortFilter.create(
            uid=coe_advisor_uid,
            name=name,
            filter_criteria={
                'groupCodes': ['WWP', 'MWP'],
            },
        )
        # Verify deletion
        cohort_id = cohort['id']
        response = client.delete(f'/api/cohort/delete/{cohort_id}')
        assert response.status_code == 200
        cohorts = all_cohorts_owned_by(asc_advisor_uid)
        assert not next((c for c in cohorts if c['id'] == cohort_id), None)


class TestCohortPerFilters:
    """Cohort API."""

    @classmethod
    def _post(cls, client, json_data=()):
        return client.post(
            '/api/cohort/get_students_per_filters',
            data=json.dumps(json_data),
            content_type='application/json',
        )

    def test_students_per_filters_not_authenticated(self, client):
        """API requires authentication."""
        assert self._post(client).status_code == 401

    def test_students_per_filters_with_empty(self, client, coe_advisor_session):
        """API requires non-empty input."""
        assert self._post(client, {'filters': []}).status_code == 400

    def test_students_per_filters_unauthorized(self, client, asc_advisor_session):
        """ASC advisor is not allowed to query with COE attributes."""
        response = self._post(
            client,
            {
                'filters':
                    [
                        {
                            'key': 'coeProbation',
                            'type': 'boolean',
                            'value': 'true',
                        },
                    ],
            },
        )
        assert response.status_code == 403

    def test_students_per_filters_coe_advisor(self, client, coe_advisor_session):
        """API translates 'coeProbation' filter to proper filter_criteria query."""
        gpa_range_1 = 'numrange(0, 2, \'[)\')'
        gpa_range_2 = 'numrange(2, 2.5, \'[)\')'
        response = self._post(
            client,
            {
                'filters':
                    [
                        {
                            'key': 'coeProbation',
                            'type': 'boolean',
                            'value': 'true',
                        },
                        {
                            'key': 'gpaRanges',
                            'type': 'array',
                            'value': gpa_range_1,
                        },
                        {
                            'key': 'gpaRanges',
                            'type': 'array',
                            'value': gpa_range_2,
                        },
                        {
                            'key': 'lastNameRange',
                            'type': 'range',
                            'value': ['A', 'Z'],
                        },
                    ],
            },
        )
        assert response.status_code == 200
        cohort = response.json
        assert 'totalStudentCount' in cohort
        assert 'students' in cohort
        criteria = cohort['criteria']
        assert criteria['coeProbation'] is not None
        assert criteria['lastNameRange'] is not None
        gpa_ranges = criteria['gpaRanges']
        assert len(gpa_ranges) == 2
        assert gpa_range_1 in gpa_ranges
        assert gpa_range_2 in gpa_ranges
        for key in [
            'advisorLdapUids',
            'ethnicities',
            'expectedGradTerms',
            'genders',
            'groupCodes',
            'inIntensiveCohort',
            'isInactiveAsc',
            'levels',
            'majors',
            'transfer',
            'underrepresented',
            'unitRanges',
        ]:
            assert criteria[key] is None

    def _get_defensive_line(self, client, inactive_asc, order_by):
        response = self._post(
            client,
            {
                'filters':
                    [
                        {
                            'key': 'groupCodes',
                            'type': 'array',
                            'value': 'MFB-DL',
                        },
                        {
                            'key': 'isInactiveAsc',
                            'type': 'boolean',
                            'value': inactive_asc,
                        },
                    ],
                'orderBy': order_by,
            },
        )
        assert response.status_code == 200
        return response.json['students']

    def test_students_per_filters_order_by(self, client, asc_advisor_session):
        def _get_first_student(order_by):
            students = self._get_defensive_line(client, False, order_by)
            assert len(students) == 3
            return students[0]
        assert _get_first_student('first_name')['firstName'] == 'Dave'
        assert _get_first_student('last_name')['lastName'] == 'Doolittle'
        assert _get_first_student('gpa')['cumulativeGPA'] == 3.005
        assert _get_first_student('level')['level'] == 'Junior'
        assert _get_first_student('major')['majors'][0] == 'Chemistry BS'
        assert _get_first_student('units')['cumulativeUnits'] == 34
        student = _get_first_student('group_name')
        assert student['athleticsProfile']['athletics'][0]['groupName'] == 'Football, Defensive Backs'

    def test_student_athletes_inactive_asc(self, client, asc_advisor_session):
        """An ASC advisor query defaults to active athletes only."""
        students = self._get_defensive_line(client, False, 'gpa')
        assert len(students) == 3
        for student in students:
            assert student['athleticsProfile']['isActiveAsc'] is True

    def test_student_athletes_inactive_admin(self, client, admin_session):
        """An admin query defaults to active and inactive athletes."""
        students = self._get_defensive_line(client, None, 'gpa')
        assert len(students) == 4

        def is_active_asc(student):
            return student['athleticsProfile']['isActiveAsc']
        assert is_active_asc(students[0]) is False
        assert is_active_asc(students[1]) is True
        assert is_active_asc(students[2]) is True
        assert is_active_asc(students[3]) is True

    def test_filter_expected_grad_term(self, client, coe_advisor_session):
        response = self._post(
            client,
            {
                'filters':
                    [
                        {
                            'key': 'expectedGradTerms',
                            'type': 'array',
                            'value': '2202',
                        },
                    ],
            },
        )
        assert len(response.json['students']) == 2
        for student in response.json['students']:
            assert student['expectedGraduationTerm']['name'] == 'Spring 2020'

    def test_filter_transfer(self, client, coe_advisor_session):
        response = self._post(
            client,
            {
                'filters':
                    [
                        {
                            'key': 'transfer',
                            'type': 'boolean',
                            'value': True,
                        },
                    ],
            },
        )
        assert len(response.json['students']) == 2
        for student in response.json['students']:
            assert student['transfer'] is True
