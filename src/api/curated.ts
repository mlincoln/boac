import _ from 'lodash'
import axios from 'axios'
import moment from 'moment-timezone'
import utils from '@/api/api-utils'
import Vue from 'vue'

const $_onCreate = group => {
  Vue.prototype.$currentUser.myCuratedGroups.push(group)
  Vue.prototype.$eventHub.emit('my-curated-groups-updated')
}

const $_onDelete = groupId => {
  const indexOf = Vue.prototype.$currentUser.myCuratedGroups.findIndex(curatedGroup => curatedGroup.id === groupId)
  Vue.prototype.$currentUser.myCuratedGroups.splice(indexOf, 1)
  Vue.prototype.$eventHub.emit('my-curated-groups-updated')
}

const $_onUpdate = updatedGroup => {
  const group = Vue.prototype.$currentUser.myCuratedGroups.find(group => group.id === +updatedGroup.id)
  Object.assign(group, updatedGroup)
  Vue.prototype.$eventHub.emit('my-curated-groups-updated')
}

export function addStudents(curatedGroupId: number, sids: string[], returnStudentProfiles?: boolean) {
  return axios
    .post(`${utils.apiBaseUrl()}/api/curated_group/students/add`, {
      curatedGroupId: curatedGroupId,
      sids: sids,
      returnStudentProfiles: returnStudentProfiles
    })
    .then(response => {
      const group = response.data
      group.sids = _.uniq(group.sids.concat(sids))
      return group
    })
}

export function createCuratedGroup(name: string, sids: string[]) {
  return axios
    .post(`${utils.apiBaseUrl()}/api/curated_group/create`, {
      name: name,
      sids: sids
    })
    .then(function(response) {
      const group = response.data
      $_onCreate(group)
      return group
    })
}

export function deleteCuratedGroup(id) {
  return axios
    .delete(`${utils.apiBaseUrl()}/api/curated_group/delete/${id}`, {
      headers: {
        'Content-Type': 'application/json'
      }
    })
    .then(() => {
      $_onDelete(id)
      Vue.prototype.$ga.curatedEvent(id, null, 'delete')
    })
    .catch(error => error)
}

export function downloadCuratedGroupCsv(id: number, name: string, csvColumnsSelected: any[]) {
  const fileDownload = require('js-file-download')
  const now = moment().format('YYYY-MM-DD_HH-mm-ss')
  return axios
    .post(`${utils.apiBaseUrl()}/api/curated_group/${id}/download_csv`, {csvColumnsSelected})
    .then(response => fileDownload(response.data, `${name}-students-${now}.csv`), () => null)
}

export function getCuratedGroup(
  id: number,
  orderBy: string,
  termId: string,
  offset: number,
  limit: number
) {
  const url = `${utils.apiBaseUrl()}/api/curated_group/${id}?orderBy=${orderBy}&termId=${termId}&offset=${offset}&limit${limit}`
  return axios.get(url).then(response => response.data, () => null)
}

export function getUsersWithGroups() {
  return axios
    .get(`${utils.apiBaseUrl()}/api/curated_groups/all`)
    .then(response => response.data, () => null)
}

export function removeFromCuratedGroup(groupId, sid) {
  return axios
    .delete(`${utils.apiBaseUrl()}/api/curated_group/${groupId}/remove_student/${sid}`)
    .then(response => {
      const group = response.data
      group.sids = _.remove(group.sids, s => sid === s)
      Vue.prototype.$ga.curatedEvent(group.id, group.name, 'remove_student')
      return group
    })
}

export function renameCuratedGroup(id, name) {
  return axios
    .post(`${utils.apiBaseUrl()}/api/curated_group/rename`, {id: id, name: name})
    .then(response => {
      const group = response.data
      $_onUpdate(group)
      Vue.prototype.$ga.curatedEvent(group.id, group.name, 'rename')
      return group
    })
    .catch(error => error)
}

export function getStudentsWithAlerts(groupId) {
  return axios
    .get(`${utils.apiBaseUrl()}/api/curated_group/${groupId}/students_with_alerts`)
    .then(response => response.data, () => null)
}
