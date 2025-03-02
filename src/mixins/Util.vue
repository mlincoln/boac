<script>
import _ from 'lodash'
import moment from 'moment-timezone'
import numeral from 'numeral'

const decodeHtml = (snippet) => {
  if (snippet && snippet.indexOf('&') > 0) {
    const el = document.createElement('textarea')
    el.innerHTML = snippet
    return el.value
  } else {
    return snippet
  }
}

const toInt = (value, defaultValue = null) => {
  const parsed = parseInt(value, 10)
  return Number.isInteger(parsed) ? parsed : defaultValue
}

const toBoolean = value => value && value !== 'false'

export default {
  name: 'Util',
  methods: {
    describeCuratedGroupDomain(domain, capitalize) {
      const format = s => capitalize ? _.capitalize(s) : s
      return format(domain === 'admitted_students' ? 'admissions ' : 'curated ') + format('group')
    },
    escapeForRegExp: s => s && s.replace(/[.*+?^${}()|[\]\\]/g, '\\$&'),
    isNilOrBlank: s => _.isNil(s) || _.trim(s) === '',
    isToday: date => {
      return moment().diff(date, 'days') === 0
    },
    lastNameFirst: u => u.lastName && u.firstName ? `${u.lastName}, ${u.firstName}` : (u.lastName || u.firstName),
    numFormat: (num, format=null) => numeral(num).format(format),
    oxfordJoin: (arr, zeroString) => {
      switch((arr || []).length) {
      case 0: return _.isNil(zeroString) ? '' : zeroString
      case 1: return _.head(arr)
      case 2: return `${_.head(arr)} and ${_.last(arr)}`
      default: return _.join(_.concat(_.initial(arr), `and ${_.last(arr)}`), ', ')
      }
    },
    pluralize: (noun, count, substitutions = {}, pluralSuffix = 's') => {
      return (`${substitutions[count] || substitutions['other'] || count} ` + (count !== 1 ? `${noun}${pluralSuffix}` : noun))
    },
    round: (value, decimals) => (Math.round(value * Math.pow(10, decimals)) / Math.pow(10, decimals)).toFixed(decimals),
    setPageTitle: phrase => (document.title = `${phrase ? decodeHtml(phrase) : 'UC Berkeley'} | BOA`),
    sortComparator: (a, b, nullFirst=true) => {
      if (_.isNil(a) || _.isNil(b)) {
        if (nullFirst) {
          return _.isNil(a) ? (_.isNil(b) ? 0 : -1) : 1
        } else {
          return _.isNil(b) ? (_.isNil(a) ? 0 : -1) : 1
        }
      } else if (_.isNumber(a) && _.isNumber(b)) {
        return a < b ? -1 : a > b ? 1 : 0
      } else {
        const aInt = toInt(a)
        const bInt = toInt(b)
        if (aInt && bInt) {
          return aInt < bInt ? -1 : aInt > bInt ? 1 : 0
        } else {
          return a.toString().localeCompare(b.toString(), undefined, {
            numeric: true
          })
        }
      }
    },
    stripAnchorRef: fullPath => _.split(fullPath, '#', 1)[0],
    stripHtmlAndTrim: html => {
      let text = html && html.replace(/<([^>]+)>/ig,'')
      text = text && text.replace(/&nbsp;/g, '')
      return _.trim(text)
    },
    studentRoutePath: (uid, inDemoMode) => inDemoMode ? `/student/${window.btoa(uid)}` : `/student/${uid}`,
    toBoolean,
    toInt
  }
}
</script>
