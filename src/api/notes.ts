import _ from 'lodash'
import axios from 'axios'
import utils from '@/api/api-utils'
import Vue from 'vue'

const $_track = action => Vue.prototype.$ga.note(action)

export function getNote(noteId) {
  $_track('view')
  return axios
    .get(`${utils.apiBaseUrl()}/api/note/${noteId}`)
    .then(response => response.data, () => null)
}

export function markNoteRead(noteId) {
  return axios
    .post(`${utils.apiBaseUrl()}/api/notes/${noteId}/mark_read`)
    .then(response => {
      $_track('read')
      return response.data
    }, () => null)
}

export function createNotes(
    attachments: any[],
    body: string,
    cohortIds: number[],
    contactType: string,
    curatedGroupIds: number[],
    isPrivate: boolean,
    setDate: string,
    sids: any,
    subject: string,
    templateAttachmentIds: [],
    topics: string[]
) {
  const data = {
    body,
    cohortIds,
    contactType,
    curatedGroupIds,
    isPrivate,
    setDate,
    sids,
    subject,
    templateAttachmentIds,
    topics
  }
  _.each(attachments || [], (attachment, index) => data[`attachment[${index}]`] = attachment)
  const action = sids.length > 1 ? 'batch' : 'create'
  $_track(isPrivate ? `${action} private` : action)
  return utils.postMultipartFormData('/api/notes/create', data)
}

export function updateNote(
    body: string,
    contactType: string,
    isPrivate: boolean,
    noteId: number,
    setDate: string,
    subject: string,
    topics: string[]
) {
  const data = {
    body: body,
    contactType: contactType,
    id: noteId,
    isPrivate: isPrivate,
    setDate: setDate,
    subject: subject,
    topics: topics
  }
  const api_json = utils.postMultipartFormData('/api/notes/update', data)
  $_track('update')
  return api_json
}

export function deleteNote(noteId: number) {
  $_track('delete')
  return axios
    .delete(`${utils.apiBaseUrl()}/api/notes/delete/${noteId}`)
    .then(response => response.data)
}

export function addAttachments(noteId: number, attachments: any[]) {
  const data = {}
  _.each(attachments, (attachment, index) => data[`attachment[${index}]`] = attachment)
  return utils.postMultipartFormData(`/api/notes/${noteId}/attachments`, data)
}

export function removeAttachment(noteId: number, attachmentId: number) {
  return axios
    .delete(`${utils.apiBaseUrl()}/api/notes/${noteId}/attachment/${attachmentId}`)
    .then(response => response.data)
}
