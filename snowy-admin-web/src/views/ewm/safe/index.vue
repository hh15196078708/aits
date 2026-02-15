<template>
	<a-card :bordered="false" style="width: 100%">
		<a-form ref="searchFormRef" :model="searchFormState">
			<a-row :gutter="10">
				<a-col :xs="24" :sm="6" :md="6" :lg="6" :xl="6">
					<a-form-item label="IP地址" name="safeIp">
						<a-input v-model:value="searchFormState.safeIp" placeholder="请输入IP地址" />
					</a-form-item>
				</a-col>
				<!-- 客户选择下拉框 -->
				<a-col :xs="24" :sm="6" :md="6" :lg="6" :xl="6">
					<a-form-item label="所属项目" name="projectId">
						<a-select v-model:value="searchFormState.projectId" placeholder="请选择项目" allowClear>
							<a-select-option v-for="item in projectList" :key="item.id" :value="item.id">
								{{ item.projectName }}
							</a-select-option>
						</a-select>
					</a-form-item>
				</a-col>
				<!-- 新增：状态筛选 -->
				<a-col :xs="24" :sm="6" :md="6" :lg="6" :xl="6">
					<a-form-item label="设备状态" name="safeStatus">
						<a-select v-model:value="searchFormState.safeStatus" placeholder="请选择状态" allowClear>
							<a-select-option value="ON">在线</a-select-option>
							<a-select-option value="OFF">离线</a-select-option>
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
					<!-- 这里可以放置批量操作按钮 -->
				</a-space>
			</template>
			<template #bodyCell="{ column, record }">
				<!-- 新增：状态列 Tag 展示 -->
				<template v-if="column.dataIndex === 'safeStatus'">
					<a-tag :color="record.safeStatus === 'ON' ? 'green' : 'red'">
						{{ record.safeStatus === 'ON' ? '在线' : '离线' }}
					</a-tag>
				</template>

				<template v-if="column.dataIndex === 'action'">
					<a-space>
						<a @click="handleMonitor(record)">监控</a>
<!--						<a-divider type="vertical" v-if="hasPerm('ewmProjectSafeEdit')" />-->
<!--						<a @click="formRef.onOpen(record)" v-if="hasPerm('ewmProjectSafeEdit')">编辑</a>-->
<!--						<a-divider type="vertical" v-if="hasPerm(['ewmProjectSafeEdit', 'ewmProjectSafeDelete'], 'and')" />-->
<!--						<a-popconfirm title="确定要删除吗？" @confirm="deleteEwmProjectSafe(record)">-->
<!--							<a style="color: #ff4d4f" v-if="hasPerm('ewmProjectSafeDelete')">删除</a>-->
<!--						</a-popconfirm>-->
					</a-space>
				</template>
			</template>
		</s-table>
	</a-card>
</template>

<script setup name="projectsafe">
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { cloneDeep } from 'lodash-es'
import ewmProjectSafeApi from '@/api/ewm/ewmProjectSafeApi'
import ewmProjectApi from '@/api/ewm/ewmProjectApi'

const router = useRouter()
const tableRef = ref()
const searchFormState = ref({})
const searchFormRef = ref()
const formRef = ref()
const projectList = ref([])
const toolConfig = { refresh: true, height: true, columnSetting: true, striped: false }

const columns = [
	{
		title: '所属项目',
		dataIndex: 'projectName'
	},
	{
		title: '名称',
		dataIndex: 'safeName'
	},
	{
		title: '机器码',
		dataIndex: 'safeCode'
	},
	{
		title: '操作系统',
		dataIndex: 'safeOs'
	},
	{
		title: 'IP地址',
		dataIndex: 'safeIp'
	},
	{
		title: '状态',
		dataIndex: 'safeStatus'
	},
	{
		title: '授权开始时间',
		dataIndex: 'safeStartTime'
	},
	{
		title: '授权结束时间',
		dataIndex: 'safeEndTime'
	},
	{
		title: '操作',
		dataIndex: 'action',
		align: 'center',
		fixed: 'right',
		width: 200
	}
]

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

onMounted(() => {
	loadProjectList()
})

const loadData = (parameter) => {
	const searchFormParam = cloneDeep(searchFormState.value)
	// 使用 Object.assign 合并分页参数(parameter)和查询参数(searchFormParam)
	return ewmProjectSafeApi.ewmProjectSafePage(Object.assign(parameter, searchFormParam)).then((data) => {
		return data
	})
}

// 加载项目列表
const loadProjectList = () => {
	ewmProjectApi.ewmProjectPage({ current: 1, size: 9999 }).then((res) => {
		projectList.value = res.records
	})
}

// 跳转监控页面
const handleMonitor = (record) => {
	router.push({
		path: '/safe/projectsafe/monitor', // 假设 monitor.vue 对应的路由路径是这个
		query: {
			id: record.id,
			name: record.safeName
		}
	})
}



// 重置
const reset = () => {
	searchFormRef.value.resetFields()
	tableRef.value.refresh(true)
}

</script>
