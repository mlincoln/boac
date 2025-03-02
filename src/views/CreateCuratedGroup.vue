<template>
  <div class="pt-3 pr-3 pl-3">
    <h1 class="page-section-header">Create {{ domain === 'admitted_students' ? 'CE3' : 'Curated' }} Group</h1>
    <div>
      Type or paste a list of Student Identification (SID) numbers below. Example: 9999999990, 9999999991
    </div>
    <CuratedGroupBulkAdd
      :bulk-add-sids="bulkAddSids"
      :domain="domain"
      :is-saving="isSaving"
    />
    <b-modal
      v-model="showCreateModal"
      body-class="pl-0 pr-0"
      hide-footer
      hide-header
      @shown="$putFocusNextTick('modal-header')"
    >
      <CreateCuratedGroupModal
        :cancel="cancel"
        :create="create"
        :domain="domain"
      />
    </b-modal>
  </div>
</template>

<script>
import Context from '@/mixins/Context'
import CreateCuratedGroupModal from '@/components/curated/CreateCuratedGroupModal'
import CuratedGroupBulkAdd from '@/components/curated/CuratedGroupBulkAdd.vue'
import Util from '@/mixins/Util'
import {createCuratedGroup} from '@/api/curated'

export default {
  name: 'CreateCuratedGroup',
  components: {CreateCuratedGroupModal, CuratedGroupBulkAdd},
  mixins: [Context, Util],
  data: () => ({
    domain: undefined,
    isSaving: false,
    showCreateModal: false,
    sids: undefined
  }),
  created() {
    this.domain = this.$route.query.domain || 'default'
  },
  methods: {
    bulkAddSids(sids) {
      this.isSaving = true
      this.sids = sids
      this.showCreateModal = true
    },
    cancel() {
      this.showCreateModal = false
      this.isSaving = false
      this.$announcer.polite(`You have canceled the operation to create a new ${this.describeCuratedGroupDomain(this.domain)}.`)
      this.$putFocusNextTick('curated-group-bulk-add-sids')
    },
    create(name) {
      this.showCreateModal = false
      createCuratedGroup(this.domain, name, this.sids)
        .then(group => {
          this.$announcer.polite(`Curated group '${name}' created. It has ${this.sids.length} students.`)
          this.isSaving = false
          this.$router.push(`/curated/${group.id}`)
        })
    }
  }
}
</script>
