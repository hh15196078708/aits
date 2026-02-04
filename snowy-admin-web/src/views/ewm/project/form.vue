<template>
	<xn-form-container
		:title="formData.id ? '编辑项目表' : '增加项目表'"
		:width="900"
		v-model:open="open"
		:destroy-on-close="true"
		@close="onClose"
	>
		<a-form ref="formRef" :model="formData" :rules="formRules" layout="vertical">
			<a-row :gutter="16">
				<a-col :xs="24" :sm="24" :md="24" :lg="24" :xl="24">
					<a-form-item label="项目名称：" name="projectName">
						<a-input v-model:value="formData.projectName" placeholder="请输入项目名称" allow-clear />
					</a-form-item>
				</a-col>
				<a-col :xs="24" :sm="24" :md="12" :lg="12" :xl="12">
					<a-form-item label="项目负责人：" name="projectLeader">
						<a-input v-model:value="formData.projectLeader" placeholder="请输入项目负责人" allow-clear />
					</a-form-item>
				</a-col>
				<a-col :xs="24" :sm="24" :md="12" :lg="12" :xl="12">
					<a-form-item label="联系方式：" name="projectLeaderPhone">
						<a-input v-model:value="formData.projectLeaderPhone" placeholder="请输入联系方式" allow-clear />
					</a-form-item>
				</a-col>
				<a-col :xs="24" :sm="24" :md="12" :lg="12" :xl="12">
					<a-form-item label="项目金额：" name="projectMoney">
						<a-input type="number" v-model:value="formData.projectMoney" placeholder="请输入项目金额" allow-clear prefix="￥" suffix="RMB" />
					</a-form-item>
				</a-col>
				<a-col :xs="24" :sm="24" :md="12" :lg="12" :xl="12">
					<a-form-item label="排序码：" name="sortCode">
						<a-input type="number" v-model:value="formData.sortCode" placeholder="请输入排序码" allow-clear />
					</a-form-item>
				</a-col>
<!--				<a-col :xs="24" :sm="24" :md="12" :lg="12" :xl="12">-->
<!--					<a-form-item label="扩展信息：" name="extJson">-->
<!--						<a-input v-model:value="formData.extJson" placeholder="请输入扩展信息" allow-clear />-->
<!--					</a-form-item>-->
<!--				</a-col>-->
				<a-col :xs="24" :sm="24" :md="24" :lg="24" :xl="24">
					<a-form-item label="所属组织：" name="orgId">
						<a-tree-select
							v-model:value="formData.orgId"
							class="xn-wd"
							:dropdown-style="{ maxHeight: '400px', overflow: 'auto' }"
							placeholder="请选择所属组织"
							allow-clear
							tree-default-expand-all
							:tree-data="treeData"
							:field-names="{
						children: 'children',
						label: 'name',
						value: 'id'
					}"
							selectable="false"
							tree-line
						/>
					</a-form-item>
				</a-col>
				<a-col :xs="24" :sm="24" :md="12" :lg="12" :xl="12">
					<a-form-item label="项目状态" name="projectStatus">
						<a-select v-model:value="formData.projectStatus" placeholder="请选择项目状态" :options="peojectStatusOptions" />
					</a-form-item>
				</a-col>
				<a-col :xs="24" :sm="24" :md="12" :lg="12" :xl="12">
					<a-form-item label="项目类别" name="projectType">
						<a-select v-model:value="formData.projectType" placeholder="请选择项目类别" :options="peojectTypeOptions" />
<!--						<a-input v-model:value="formData.projectType" placeholder="请输入项目类别" allow-clear />-->
					</a-form-item>
				</a-col>
				<a-col :xs="24" :sm="24" :md="12" :lg="12" :xl="12">
					<a-form-item label="项目开始日期：" name="projectStartTime">
						<a-date-picker v-model:value="formData.projectStartTime" value-format="YYYY-MM-DD" placeholder="请选择项目开始日期" style="width: 100%" />
					</a-form-item>
				</a-col>
				<a-col :xs="24" :sm="24" :md="12" :lg="12" :xl="12">
					<a-form-item label="项目结束日期：" name="projectEndTime">
						<a-date-picker v-model:value="formData.projectEndTime" value-format="YYYY-MM-DD" placeholder="请选择项目结束日期" style="width: 100%" />
					</a-form-item>
				</a-col>
				<a-col :xs="24" :sm="24" :md="24" :lg="24" :xl="24">
					<a-form-item label="项目附件：" name="projectFiles">
						<xn-upload v-model:value="formData.projectFiles"
								   uploadMode="drag" :uploadNumber="9"
								   uploadText="附件上传"
								   uploadResultCategory="array"
								   :completeResult="true"
						/>
					</a-form-item>
				</a-col>
				<a-col :xs="24" :sm="24" :md="24" :lg="24" :xl="24">
					<a-form-item label="项目说明：" name="projectDesc">
						<xn-editor v-model:value="formData.projectDesc" placeholder="请输入项目说明" />
					</a-form-item>
				</a-col>
			</a-row>
		</a-form>
		<template #footer>
			<a-button style="margin-right: 8px" @click="onClose">关闭</a-button>
			<a-button style="margin-right: 8px" @click="onModel">弹框</a-button>
			<a-button type="primary" @click="onSubmit" :loading="submitLoading">保存</a-button>
		</template>
	</xn-form-container>
	<a-modal
		v-model:visible="modelVisible"
		title="Basic Modal"
		@ok="handleOk"
		width="100%"
		wrapClassName="full-modal"
	>
		<xd-file-manger
			:initial-files="mockData"
			@upload="onUpload"
			@delete="onDelete"
			@move="onMove"
		>

		</xd-file-manger>
	</a-modal>
</template>

<script setup name="ewmProjectForm">
import XdFileManger from "@/components/XdFileManger/index.vue"
import tool from '@/utils/tool'
import { cloneDeep } from 'lodash-es'
import { required } from '@/utils/formRules'
import ewmProjectApi from '@/api/ewm/ewmProjectApi'
import orgApi from "@/api/sys/orgApi";
// 抽屉状态
const open = ref(false)
const modelVisible = ref(false)
const emit = defineEmits({ successful: null })
const formRef = ref()
// 表单数据
const formData = ref({
	sortCode:99
})
const submitLoading = ref(false)
const orgIdOptions = ref([])
const peojectStatusOptions = ref([])
const peojectTypeOptions = ref([])
// 定义机构元素
const treeData = ref([])
const mockData = ref([])
const onUpload = (file) => {}
const onDelete = (file) => {}
const onMove = (file) => {}
// 打开抽屉
const onOpen = (record) => {
	open.value = true
	if (record) {
		let recordData = cloneDeep(record)
		console.log(recordData)
		const param = {
			id: recordData.id
		}
		ewmProjectApi.ewmProjectDetail(param).then((res) => {
			if(tool.isNotEmpty(res.projectFiles)){
				res.projectFiles = JSON.parse(res.projectFiles)
			}
			formData.value = Object.assign({}, res)
		})
		console.log(formData.value)
		//
		// if(tool.isNotEmpty(recordData.projectFiles)){
		// 	recordData.projectFiles = JSON.parse(recordData.projectFiles)
		// }
		// formData.value = Object.assign({}, recordData)
	}
	// orgIdOptions.value = tool.dictList('ORG_CATEGORY')
	peojectStatusOptions.value = tool.dictList('PROJECT_STATUS')
	peojectTypeOptions.value = tool.dictList('PROJECT_TYPE')
	// 获取机构树并加入顶级
	orgApi.orgOrgTreeSelector().then((res) => {
		treeData.value = [
			{
				id: 0,
				parentId: '-1',
				name: '顶级',
				children: res
			}
		]
	})
}
// 关闭抽屉
const onClose = () => {
	formRef.value.resetFields()
	formData.value = {}
	open.value = false
}
// 默认要校验的
const formRules = {
	projectName: [required('请输入项目名称')],
	projectLeader: [required('请输入项目负责人')],
	orgId: [required('请选择机构id')],
	projectStatus: [required('请选择项目状态')],
	projectType: [required('请选择项目类别')],
}
const handleOk = () => {
}
const onModel = () =>{
	modelVisible.value = true
}
// 验证并提交数据
const onSubmit = () => {
	formRef.value
		.validate()
		.then(() => {
			submitLoading.value = true
			const formDataParam = cloneDeep(formData.value)
			if (formDataParam.projectFiles && Array.isArray(formDataParam.projectFiles) && formDataParam.projectFiles.length >= 1) {
				formDataParam.projectFiles = JSON.stringify(formDataParam.projectFiles)
			}
			ewmProjectApi
				.ewmProjectSubmitForm(formDataParam, formDataParam.id)
				.then(() => {
					onClose()
					emit('successful')
				})
				.finally(() => {
					submitLoading.value = false
				})
		})
		.catch(() => {})
}
// 抛出函数
defineExpose({
	onOpen
})
</script>
