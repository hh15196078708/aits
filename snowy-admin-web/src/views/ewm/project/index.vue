<template>
	<a-card :bordered="false" style="width: 100%">
		<a-form ref="searchFormRef" :model="searchFormState">
			<a-row :gutter="10">
				<a-col :xs="24" :sm="6" :md="6" :lg="6" :xl="6">
					<a-form-item label="项目名称" name="projectName">
						<a-input v-model:value="searchFormState.projectName" placeholder="请输入项目名称" />
					</a-form-item>
				</a-col>
				<a-col :xs="24" :sm="6" :md="6" :lg="6" :xl="6">
					<a-form-item label="项目负责人" name="projectLeader">
						<a-input v-model:value="searchFormState.projectLeader" placeholder="请输入项目负责人" />
					</a-form-item>
				</a-col>
				<!-- 新增客户选择下拉框 -->
				<a-col :span="6">
					<a-form-item label="所属客户" name="clientId">
						<a-select v-model:value="searchFormState.clientId" placeholder="请选择客户" allowClear>
							<a-select-option v-for="item in clientList" :key="item.id" :value="item.id">
								{{ item.name }}
							</a-select-option>
						</a-select>
					</a-form-item>
				</a-col>


				<a-col :xs="24" :sm="6" :md="6" :lg="6" :xl="6">
					<a-form-item>
						<a-space>
							<a-button type="primary" @click="tableRef.refresh(true)">
								<template #icon><SearchOutlined /></template>
								查询
							</a-button>
							<a-button @click="reset">
								<template #icon><redo-outlined /></template>
								重置
							</a-button>
						</a-space>
					</a-form-item>
				</a-col>
			</a-row>
		</a-form>
		<s-table
			ref="tableRef"
			:columns="columns"
			:data="loadData"
			:alert="options.alert.show"
			bordered
			:row-key="(record) => record.id"
			:tool-config="toolConfig"
			:row-selection="options.rowSelection"
			:scroll="{ x: 'max-content' }"
		>
			<template #operator class="table-operator">
				<a-space>
					<a-button type="primary" @click="formRef.onOpen()" v-if="hasPerm('ewmProjectAdd')">
						<template #icon><plus-outlined /></template>
						新增
					</a-button>
<!--					<a-button @click="importModelRef.onOpen()" v-if="hasPerm('ewmProjectImport')">-->
<!--						<template #icon><import-outlined /></template>-->
<!--						<span>导入</span>-->
<!--					</a-button>-->
<!--					<a-button @click="exportData" v-if="hasPerm('ewmProjectExport')">-->
<!--						<template #icon><export-outlined /></template>-->
<!--						<span>导出</span>-->
<!--					</a-button>-->
					<xn-batch-button
						v-if="hasPerm('ewmProjectBatchDelete')"
						buttonName="批量删除"
						icon="DeleteOutlined"
						buttonDanger
						:selectedRowKeys="selectedRowKeys"
						@batchCallBack="deleteBatchEwmProject"
					/>
				</a-space>
			</template>
			<template #bodyCell="{ column, record }">
<!--				<template v-if="column.dataIndex === 'orgId'">-->
<!--					{{ $TOOL.dictTypeData('ORG_CATEGORY', record.orgId) }}-->
<!--				</template>-->
				<template v-if="column.dataIndex === 'projectType'">
					{{ $TOOL.dictTypeData('PROJECT_TYPE', record.projectType) }}
				</template>
				<template v-if="column.dataIndex === 'projectStatus'">
					{{ $TOOL.dictTypeData('PROJECT_STATUS', record.projectStatus) }}
				</template>
				<template v-if="column.dataIndex === 'projectEwm'">
					<a-image
						:width="80"
						:height="80"
						:src="record.projectEwm"
						fallback="data:image/png;base64,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"
					/>
				</template>
				<template v-if="column.dataIndex === 'action'">
					<a-space>
						<a @click="formRef.onOpen(record)" v-if="hasPerm('ewmProjectEdit')">编辑</a>
						<a-divider type="vertical" v-if="hasPerm(['ewmProjectEdit', 'ewmProjectDelete'], 'and')" />
						<a-popconfirm title="确定要删除吗？" @confirm="deleteEwmProject(record)">
							<a-button type="link" danger size="small" v-if="hasPerm('ewmProjectDelete')">删除</a-button>
						</a-popconfirm>
					</a-space>
				</template>
			</template>
		</s-table>
	</a-card>
	<Form ref="formRef" @successful="tableRef.refresh()" />
</template>

<script setup name="project">

import tool from '@/utils/tool'
import { cloneDeep } from 'lodash-es'
import Form from './form.vue'
import downloadUtil from '@/utils/downloadUtil'
import ewmProjectApi from '@/api/ewm/ewmProjectApi'
import ewmClientApi from '@/api/ewm/ewmClientApi'
const searchFormState = ref({})
const searchFormRef = ref()
const tableRef = ref()
const importModelRef = ref()
const formRef = ref()
// 客户列表数据
const clientList = ref([])
const toolConfig = { refresh: true, height: true, columnSetting: true, striped: false }
const columns = [
	{
		title: '项目名称',
		dataIndex: 'projectName'
	},
	{
		title: '项目负责人',
		dataIndex: 'projectLeader'
	},
	{
		title: '所属客户',
		dataIndex: 'clientName'
	},
	{
		title: '所属机构',
		dataIndex: 'orgName'
	},
	{
		title: '项目状态',
		dataIndex: 'projectStatus'
	},
	{
		title: '项目类别',
		dataIndex: 'projectType'
	},
	{
		title: '项目金额',
		dataIndex: 'projectMoney'
	},
	{
		title: '项目开始日期',
		dataIndex: 'projectStartTime'
	},
	{
		title: '项目结束日期',
		dataIndex: 'projectEndTime'
	},
	{
		title: '项目二维码',
		dataIndex: 'projectEwm'
	}
]
// 操作栏通过权限判断是否显示
if (hasPerm(['ewmProjectEdit', 'ewmProjectDelete'])) {
	columns.push({
		title: '操作',
		dataIndex: 'action',
		align: 'center',
		fixed: 'right'
	})
}
const selectedRowKeys = ref([])
// 列表选择配置
const options = {
	alert: {
		show: true,
		clear: () => {
			selectedRowKeys.value = ref([])
		}
	},
	rowSelection: {
		onChange: (selectedRowKey, selectedRows) => {
			selectedRowKeys.value = selectedRowKey
		}
	}
}
const loadData = (parameter) => {
	const searchFormParam = cloneDeep(searchFormState.value)
	return ewmProjectApi.ewmProjectPage(Object.assign(parameter, searchFormParam)).then((data) => {
		return data
	})
}
onMounted(() => {
	loadClientList()
})
// 重置
const reset = () => {
	searchFormRef.value.resetFields()
	tableRef.value.refresh(true)
}
// 删除
const deleteEwmProject = (record) => {
	let params = [
		{
			id: record.id
		}
	]
	ewmProjectApi.ewmProjectDelete(params).then(() => {
		tableRef.value.refresh(true)
	})
}
// 加载客户列表
const loadClientList = () => {
	// 假设这里调用的是不分页的列表接口，如果没有请使用分页接口并将size设置大一点
	ewmClientApi.ewmClientPage({ current: 1, size: 999 }).then((res) => {
		clientList.value = res.records
	})
}
// 导出
const exportData = () => {
	if (selectedRowKeys.value.length > 0) {
		const params = selectedRowKeys.value.map((m) => {
			return {
				id: m
			}
		})
		ewmProjectApi.ewmProjectExport(params).then((res) => {
			downloadUtil.resultDownload(res)
		})
	} else {
		ewmProjectApi.ewmProjectExport([]).then((res) => {
			downloadUtil.resultDownload(res)
		})
	}
}
// 批量删除
const deleteBatchEwmProject = (params) => {
	ewmProjectApi.ewmProjectDelete(params).then(() => {
		tableRef.value.clearRefreshSelected()
	})
}
</script>
