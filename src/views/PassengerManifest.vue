<template>
  <div class="p-3">
    <Spinner />
    <div v-if="!loading">
      <div class="list-group">
        <div class="align-items-baseline d-flex mb-3 mt-2">
          <div class="pr-2">
            <font-awesome :style="{color: '#3b7ea5'}" icon="address-card" size="2x" />
          </div>
          <div class="align-items-baseline d-flex">
            <div class="pr-2">
              <h1 id="dept-users-section" class="page-section-header">
                Passenger Manifest
              </h1>
            </div>
            <div class="pt-0">
              <span class="font-size-14 text-black-50">(<a id="download-boa-users-csv" :href="`${$config.apiBaseUrl}/api/users/csv`">download</a>)</span>
            </div>
          </div>
          <div class="flex-grow-1 text-right">
            <EditUserProfileModal
              :after-update-user="afterCreateUser"
              :departments="departments"
            />
          </div>
        </div>
        <Users :departments="departments" :refresh="refreshUsers" />
      </div>
    </div>
  </div>
</template>

<script>
import Context from '@/mixins/Context'
import EditUserProfileModal from '@/components/admin/EditUserProfileModal'
import Loading from '@/mixins/Loading'
import Spinner from '@/components/util/Spinner'
import Users from '@/components/admin/Users'
import Util from '@/mixins/Util'
import {getDepartments} from '@/api/user'

export default {
  name: 'PassengerManifest',
  components: {EditUserProfileModal, Spinner, Users},
  mixins: [Context, Loading, Util],
  data: () => ({
    departments: undefined,
    refreshUsers: false
  }),
  created() {
    getDepartments(true).then(departments => {
      this.departments = departments
      this.loaded('Passenger Manifest has loaded')
    })
  },
  methods: {
    afterCreateUser(name) {
      this.refreshUsers = true
      this.$announcer.polite(`${name} has been added to BOA.`)
    }
  }
}
</script>
