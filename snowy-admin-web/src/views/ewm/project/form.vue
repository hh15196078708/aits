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
					<a-form-item label="所属客户：" name="clientId">
						<a-select v-model:value="formData.clientId" placeholder="请选择客户" allow-clear>
							<a-select-option v-for="item in clientList" :key="item.id" :value="item.id">{{ item.name }}</a-select-option>
						</a-select>
					</a-form-item>
				</a-col>
				<a-col :xs="24" :sm="24" :md="12" :lg="12" :xl="12">
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
					<a-form-item label="客户经办人：" name="projectCustomer">
						<a-input v-model:value="formData.projectCustomer" placeholder="请输入客户经办人" allow-clear />
					</a-form-item>
				</a-col>
				<a-col :xs="24" :sm="24" :md="12" :lg="12" :xl="12">
					<a-form-item label="客户联系方式：" name="projectCustomerPhone">
						<a-input v-model:value="formData.projectCustomerPhone" placeholder="请输入客户联系方式" allow-clear />
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

				<a-col :xs="24" :sm="24" :md="12" :lg="12" :xl="12">
					<a-form-item label="项目状态" name="projectStatus">
						<a-select v-model:value="formData.projectStatus" placeholder="请选择项目状态" :options="peojectStatusOptions" />
					</a-form-item>
				</a-col>
				<a-col :xs="24" :sm="24" :md="12" :lg="12" :xl="12">
					<a-form-item label="项目类别" name="projectType">
						<a-select v-model:value="formData.projectType" placeholder="请选择项目类别" :options="peojectTypeOptions" />
					</a-form-item>
				</a-col>
				<a-col :xs="24" :sm="24" :md="12" :lg="12" :xl="12">
					<a-form-item label="项目开始日期：" name="projectStartTime">
						<a-date-picker v-model:value="formData.projectStartTime" value-format="YYYY-MM-DD" placeholder="请选择项目开始日期" style="width: 100%" />
					</a-form-item>
				</a-col>
				<a-col :xs="24" :sm="24" :md="12" :lg="12" :xl="12">
					<a-form-item label="项目验收日期：" name="projectAcceptTime">
						<a-date-picker v-model:value="formData.projectAcceptTime" value-format="YYYY-MM-DD" placeholder="请选择项目结束日期" style="width: 100%" />
					</a-form-item>
				</a-col>
				<a-col :xs="24" :sm="24" :md="24" :lg="24" :xl="24">
					<a-form-item label="项目附件：" name="projectFiles">
						<div class="border rounded p-2 bg-gray-50 flex flex-wrap gap-2 min-h-[40px]">
							<a-tag
								v-for="(file, index) in formData.projectFiles"
								:key="file.id"
								closable
								color="blue"
								@close="formData.projectFiles.splice(index, 1)"
							>
								<template #icon>
									<FolderOutlined v-if="file.isFolder" />
									<PaperClipOutlined v-else />
								</template>
								{{ file.name }}
							</a-tag>
							<a-button type="dashed" size="small" @click="onModel">
								<PlusOutlined /> 添加项目文件
							</a-button>
						</div>
					</a-form-item>
				</a-col>
<!--				<a-col :xs="24" :sm="24" :md="24" :lg="24" :xl="24">-->
<!--					<a-form-item label="项目附件：" name="projectFiles">-->
<!--						<xn-upload v-model:value="formData.projectFiles"-->
<!--								   uploadMode="drag" :uploadNumber="9"-->
<!--								   uploadText="附件上传"-->
<!--								   uploadResultCategory="array"-->
<!--								   :completeResult="true"-->
<!--						/>-->
<!--					</a-form-item>-->
<!--				</a-col>-->
				<a-col :xs="24" :sm="24" :md="24" :lg="24" :xl="24">
					<a-form-item label="项目说明：" name="projectDesc">
						<xn-editor v-model:value="formData.projectDesc" placeholder="请输入项目说明" />
					</a-form-item>
				</a-col>
			</a-row>
		</a-form>
		<template #footer>
			<a-button style="margin-right: 8px" @click="onClose">关闭</a-button>
			<a-button type="primary" @click="onSubmit" :loading="submitLoading">保存</a-button>
		</template>
	</xn-form-container>
	<a-modal
		v-model:visible="modelVisible"
		title="文件管理"
		@ok="handleOk"
		width="700"
		:footer="null"
	>
		<xd-file-manger
			:isSelector="true"
			selectType="all"
			:multiple="true"
			@onSelect="handleFileSelected"
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
import ewmClientApi from '@/api/ewm/ewmClientApi'
import orgApi from "@/api/sys/orgApi";
import { PlusOutlined, PaperClipOutlined } from '@ant-design/icons-vue'
import {message} from 'ant-design-vue';
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
const clientList = ref([])
// 定义机构元素
const treeData = ref([])
const mockData = ref([])
const onUpload = (file) => {}
const onDelete = (file) => {}
const onMove = (file) => {}
// 打开抽屉
const onOpen = (record) => {
	open.value = true
	formData.value = {
		sortCode: 99,
		projectFiles: [],
	}
	if (record) {
		let recordData = cloneDeep(record)
		console.log(recordData)
		const param = {
			id: recordData.id
		}
		ewmProjectApi.ewmProjectDetail(param).then((res) => {
			// 后端存储的是字符串，前端回显需要转为对象数组
			if(tool.isNotEmpty(res.projectFiles)){
				try {
					res.projectFiles = JSON.parse(res.projectFiles)
				} catch (e) {
					res.projectFiles = []
				}
			} else {
				res.projectFiles = []
			}
			// if(tool.isNotEmpty(res.projectFiles)){
			// 	res.projectFiles = JSON.parse(res.projectFiles)
			// }
			formData.value = Object.assign({}, res)
		})

	}
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
	loadClientList()
}
// 关闭抽屉
const onClose = () => {
	formRef.value.resetFields()
	formData.value = {}
	open.value = false
}
// 获取客户列表
const loadClientList = () => {
	ewmClientApi.ewmClientPage({ current: 1, size: 999 }).then((res) => {
		clientList.value = res.records
	})
}
// 默认要校验的
const formRules = {
	projectName: [required('请输入项目名称')],
	projectLeader: [required('请输入项目负责人')],
	orgId: [required('请选择机构id')],
	clientId: [required('请选择所属客户')],
	projectStatus: [required('请选择项目状态')],
	projectType: [required('请选择项目类别')],
}
const handleFileSelected = (files) => {
	// 确保 projectFiles 是数组
	if (!formData.value.projectFiles) {
		formData.value.projectFiles = []
	}

	// 将新选中的文件与已有的合并，并根据 ID 去重
	const newFiles = Array.isArray(files) ? files : [files]

	newFiles.forEach(newFile => {
		const isExist = formData.value.projectFiles.some(item => item.id === newFile.id)
		if (!isExist) {
			formData.value.projectFiles.push({
				id: newFile.id,
				name: newFile.name
			})
		}
	})

	modelVisible.value = false
	message.success(`已关联 ${newFiles.length} 个文件`)
};
// 增加删除已选文件的函数
const removeFile = (index) => {
	formData.value.projectFiles.splice(index, 1)
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
			}else{
				formDataParam.projectFiles = null
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
<style scoped>
.file-display-container {
	background-color: #fafafa;
	border: 1px solid #f0f0f0;
	padding: 12px;
	border-radius: 4px;
}
/* 如果你使用了 Tailwind，上面的 class 已经处理了布局 */
.flex { display: flex; }
.flex-wrap { flex-wrap: wrap; }
.gap-2 { gap: 0.5rem; }
.items-center { align-items: center; }
</style>
