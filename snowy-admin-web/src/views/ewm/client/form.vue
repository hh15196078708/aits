<template>
	<xn-form-container
		:title="formData.id ? '编辑客户' : '增加客户'"
		:width="700"
		:visible="visible"
		:destroy-on-close="true"
		@close="onClose"
	>
		<a-form ref="formRef" :model="formData" :rules="formRules" layout="vertical">
			<a-row :gutter="16">
				<a-col :xs="24" :sm="24" :md="24" :lg="24" :xl="24">
					<a-form-item label="客户单位名称：" name="name">
						<a-input v-model:value="formData.name" placeholder="请输入客户名称" allow-clear/>
					</a-form-item>
				</a-col>
				<a-col :xs="24" :sm="24" :md="12" :lg="12" :xl="12">
					<a-form-item label="组织类型" name="orgType">
						<a-select v-model:value="formData.orgType" placeholder="请选择组织类型"
								  :options="orgTypeOptions"/>
					</a-form-item>
				</a-col>

				<a-col :xs="24" :sm="24" :md="12" :lg="12" :xl="12">
					<a-form-item label="排序码：" name="sortCode">
						<a-input type="number" v-model:value="formData.sortCode" placeholder="请输入排序码"
								 allow-clear/>
					</a-form-item>
				</a-col>
				<a-col :xs="24" :sm="24" :md="24" :lg="24" :xl="24">
					<!-- 动态联系人列表 -->
					<a-form-item label="经办人与联系方式：" required>
						<div class="contact-list">
							<a-row v-for="(item, index) in contactList" :key="index" :gutter="8" class="mb-2">
								<a-col :span="10">
									<a-input v-model:value="item.name" placeholder="经办人姓名">
										<template #prefix>
											<UserOutlined class="site-form-item-icon"/>
										</template>
									</a-input>
								</a-col>
								<a-col :span="10">
									<a-input v-model:value="item.phone" placeholder="联系电话">
										<template #prefix>
											<PhoneOutlined class="site-form-item-icon"/>
										</template>
									</a-input>
								</a-col>
								<a-col :span="4" class="text-center">
									<MinusCircleOutlined
										v-if="contactList.length > 1"
										class="dynamic-delete-button"
										@click="removeContact(index)"
									/>
									<PlusOutlined
										v-if="index === contactList.length - 1"
										class="dynamic-add-button ml-2"
										@click="addContact"
									/>
								</a-col>
							</a-row>
						</div>
					</a-form-item>
				</a-col>
				<!-- 地图位置选择 -->
				<a-row :gutter="16">
					<a-col :span="24">
						<a-form-item label="单位位置：" name="address">
							<a-input-group compact>
								<a-input v-model:value="formData.longitude" style="width: 20%" placeholder="经度"
										 readonly/>
								<a-input v-model:value="formData.latitude" style="width: 20%" placeholder="纬度"
										 readonly/>
								<a-input v-model:value="formData.address" style="width: 45%"
										 placeholder="地址（选点后自动回填）" allow-clear/>
								<a-button type="primary" style="width: 15%" @click="handleOpenMap">
									<template #icon>
										<EnvironmentOutlined/>
									</template>
									选点
								</a-button>
							</a-input-group>
						</a-form-item>
					</a-col>
				</a-row>
				<a-col :xs="24" :sm="24" :md="24" :lg="24" :xl="24">
					<a-form-item label="备注：" name="remark">
						<a-textarea v-model:value="formData.remark" placeholder="请输入备注"
									:auto-size="{ minRows: 3, maxRows: 5 }"/>
					</a-form-item>
				</a-col>
			</a-row>
		</a-form>
		<template #footer>
			<a-button style="margin-right: 8px" @click="onClose">关闭</a-button>
			<a-button type="primary" @click="onSubmit" :loading="submitLoading">保存</a-button>
		</template>

		<!-- 引入地图组件 -->
		<xd-map ref="mapSelectorRef" @ok="handleMapSelect"/>
	</xn-form-container>
</template>

<script setup>
import {cloneDeep} from 'lodash-es'
import {ref} from 'vue'
import {required} from '@/utils/formRules'
import ewmClientApi from "@/api/ewm/ewmClientApi";
import {
	EnvironmentOutlined,
	MinusCircleOutlined,
	PlusOutlined,
	UserOutlined,
	PhoneOutlined
} from '@ant-design/icons-vue'
import XdMap from '@/components/XdMap/index.vue'
import {message} from 'ant-design-vue'
import tool from "@/utils/tool";

// 抽屉状态
const visible = ref(false)
const emit = defineEmits({successful: null})
const orgTypeOptions = ref([])
const formRef = ref()
// 表单数据
const formData = ref({})
const submitLoading = ref(false)
const mapSelectorRef = ref()

// 动态联系人列表 { name: string, phone: string }
const contactList = ref([{name: '', phone: ''}])

// 打开抽屉
const onOpen = (record) => {
	visible.value = true
	formData.value = {
		sortCode: 99
	}
	contactList.value = [{name: '', phone: ''}] // 重置联系人

	if (record) {
		const recordData = cloneDeep(record)
		formData.value = recordData

		// 解析联系人数据用于回显
		if (recordData.agent) {
			const agents = recordData.agent.split(',')
			const phones = recordData.phone ? recordData.phone.split(',') : []

			contactList.value = agents.map((name, i) => ({
				name: name,
				phone: phones[i] || ''
			}))
		}
	}
	orgTypeOptions.value = tool.dictList('ORG_CATEGORY')
}

// 关闭抽屉
const onClose = () => {
	formRef.value.resetFields()
	visible.value = false
}

// 默认要校验的
const formRules = {
	name: [required('请输入客户名称')],
	orgType: [required('请选择组织类型')],
}

// 添加联系人行
const addContact = () => {
	contactList.value.push({name: '', phone: ''})
}

// 删除联系人行
const removeContact = (index) => {
	contactList.value.splice(index, 1)
	if (contactList.value.length === 0) {
		addContact() // 保持至少一行
	}
}

// 验证并提交数据
const onSubmit = () => {
	// 校验联系人
	const validContacts = contactList.value.filter(item => item.name.trim() !== '')
	if (validContacts.length === 0) {
		message.warning('请至少输入一位经办人')
		return
	}

	formRef.value
		.validate()
		.then(() => {
			submitLoading.value = true
			const formDataParam = cloneDeep(formData.value)

			// 将对象数组转换为逗号分隔的字符串
			formDataParam.agent = validContacts.map(c => c.name).join(',')
			formDataParam.phone = validContacts.map(c => c.phone).join(',')

			ewmClientApi
				.ewmClientSubmitForm(formDataParam, formDataParam.id)
				.then(() => {
					onClose()
					emit('successful')
				})
				.finally(() => {
					submitLoading.value = false
				})
		})
		.catch(() => {
		})
}

// 打开地图选择器
const handleOpenMap = () => {
	const currentData = {
		lng: formData.value.longitude,
		lat: formData.value.latitude,
		address: formData.value.address
	}
	mapSelectorRef.value.open(currentData)
}

// 地图选点回调
const handleMapSelect = (data) => {
	formData.value.longitude = data.longitude
	formData.value.latitude = data.latitude
	if (data.address) {
		formData.value.address = data.address
	}
}

defineExpose({
	onOpen
})
</script>

<style scoped>
.dynamic-delete-button {
	cursor: pointer;
	position: relative;
	top: 4px;
	font-size: 20px;
	color: #999;
	transition: all 0.3s;
}

.dynamic-delete-button:hover {
	color: #ff4d4f;
}

.dynamic-add-button {
	cursor: pointer;
	position: relative;
	top: 4px;
	font-size: 20px;
	color: #1890ff;
}

.ml-2 {
	margin-left: 8px;
}

.mb-2 {
	margin-bottom: 8px;
}

.text-center {
	text-align: center;
}
</style>
