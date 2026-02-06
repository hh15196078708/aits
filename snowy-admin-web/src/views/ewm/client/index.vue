<template>
	<a-card :bordered="false">
		<a-form ref="searchFormRef" name="advanced_search" :model="searchFormState" class="ant-advanced-search-form">
			<a-row :gutter="24">
				<a-col :span="6">
					<a-form-item label="客户名称" name="name">
						<a-input v-model:value="searchFormState.name" placeholder="请输入客户名称" />
					</a-form-item>
				</a-col>
				<a-col :span="6">
					<a-form-item label="经办人" name="agent">
						<a-input v-model:value="searchFormState.agent" placeholder="请输入经办人" />
					</a-form-item>
				</a-col>
				<a-col :span="6">
					<a-button type="primary" @click="tableRef.refresh()">查询</a-button>
					<a-button style="margin-left: 8px" @click="reset">重置</a-button>
				</a-col>
			</a-row>
		</a-form>
	</a-card>
	<a-card :bordered="false" class="mt-2">
		<s-table
			ref="tableRef"
			:columns="columns"
			:data="loadData"
			:alert="options.alert.show"
			bordered
			:row-key="(record) => record.id"
			:tool-config="toolConfig"
			:row-selection="options.rowSelection"
		>
			<template #operator class="table-operator">
				<a-space>
					<a-button type="primary" @click="formRef.onOpen()" v-if="hasPerm('ewmClientAdd')">
						<template #icon><plus-outlined /></template>
						新增
					</a-button>
					<xn-batch-delete
						v-if="selectedRowKeys.length > 0"
						:selectedRowKeys="selectedRowKeys"
						@batchDelete="deleteBatchEwmClient"
					/>
				</a-space>
			</template>
			<template #bodyCell="{ column, record }">
				<template v-if="column.dataIndex === 'orgType'">
					{{ $TOOL.dictTypeData('ORG_CATEGORY', record.orgType) }}
				</template>
				<!-- 自定义渲染经办人/电话列 -->
				<template v-if="column.dataIndex === 'contacts'">
					<div style="margin-bottom: 5px" v-for="(item, index) in parseContacts(record.agent, record.phone)" :key="index">
						<a-tag color="blue">{{ item.agent }}</a-tag> : {{ item.phone }}
					</div>
				</template>
				<template v-if="column.key === 'action'">
					<a-space>
						<a @click="formRef.onOpen(record)" v-if="hasPerm('ewmClientEdit')">编辑</a>
						<a-divider type="vertical" v-if="hasPerm(['ewmClientEdit', 'ewmClientDelete'], 'and')"/>
						<a-popconfirm title="确定要删除此客户吗？" @confirm="deleteEwmClient(record)">
							<a style="color: #ff4d4f" v-if="hasPerm('ewmClientDelete')">删除</a>
						</a-popconfirm>
					</a-space>
				</template>
			</template>
		</s-table>
	</a-card>
	<Form ref="formRef" @successful="tableRef.refresh()" />
</template>

<script setup name="ewmClient">
import tool from '@/utils/tool'
import ewmClientApi from "@/api/ewm/ewmClientApi";
import Form from './form.vue'
import { ref } from 'vue'

const tableRef = ref()
const formRef = ref()
const searchFormRef = ref()
const searchFormState = ref({})
const selectedRowKeys = ref([])
const columns = [
	{
		title: '客户名称',
		dataIndex: 'name'
	},
	{
		title: '客户类别',
		dataIndex: 'orgType'
	},
	{
		title: '联系人信息',
		dataIndex: 'contacts', // 使用虚拟字段
		width: 300
	},
	{
		title: '地址',
		dataIndex: 'address',
		ellipsis: true
	},
	{
		title: '创建时间',
		dataIndex: 'createTime',
		sorter: true,
		width: 150
	},
	{
		title: '操作',
		key: 'action',
		align: 'center',
		width: 150
	}
]
const toolConfig = { refresh: true, height: true, columnSetting: true, striped: false }

// 辅助函数：解析经办人和电话
const parseContacts = (agentStr, phoneStr) => {
	if (!agentStr) return []
	const agents = agentStr.split(',')
	const phones = phoneStr ? phoneStr.split(',') : []
	return agents.map((agent, i) => ({
		agent: agent,
		phone: phones[i] || '-'
	}))
}

// 列表数据加载
const loadData = (parameter) => {
	const searchFormParam = JSON.parse(JSON.stringify(searchFormState.value))
	return ewmClientApi.ewmClientPage(Object.assign(parameter, searchFormParam)).then((data) => {
		return data
	})
}
// 重置
const reset = () => {
	searchFormRef.value.resetFields()
	tableRef.value.refresh(true)
}
// 删除
const deleteEwmClient = (record) => {
	let params = [
		{
			id: record.id
		}
	]
	ewmClientApi.ewmClientDelete(params).then(() => {
		tableRef.value.refresh()
	})
}
// 批量删除
const deleteBatchEwmClient = (params) => {
	ewmClientApi.ewmClientDelete(params).then(() => {
		tableRef.value.clearRefreshSelected()
	})
}
const options = {
	alert: {
		show: false,
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
</script>
