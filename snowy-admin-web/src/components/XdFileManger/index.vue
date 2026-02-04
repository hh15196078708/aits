<template>
	<div class="xd-file-manager flex flex-col h-full bg-white rounded-md shadow-sm border border-gray-100">
		<!-- 顶部工具栏 -->
		<div class="flex flex-col md:flex-row justify-between items-center p-3 border-b border-gray-100 gap-3">
			<!-- 左侧操作区 -->
			<div class="flex gap-2 w-full md:w-auto">
				<a-button type="primary" @click="triggerUpload">
					<template #icon><CloudUploadOutlined /></template>
					上传文件
				</a-button>
				<a-button @click="handleCreateFolder">
					<template #icon><FolderAddOutlined /></template>
					新建文件夹
				</a-button>

				<!-- 上传队列气泡 -->
				<a-popover v-if="uploadQueue.length > 0" title="上传队列" trigger="click" placement="bottomLeft">
					<template #content>
						<div class="w-72 max-h-60 overflow-y-auto custom-scrollbar">
							<div v-for="task in uploadQueue" :key="task.id" class="mb-3">
								<div class="flex justify-between text-xs mb-1 text-gray-600">
									<span class="truncate max-w-[70%]" :title="task.name">{{ task.name }}</span>
									<span>{{ task.status === 'done' ? '完成' : task.progress + '%' }}</span>
								</div>
								<a-progress
									:percent="task.progress"
									size="small"
									:status="getUploadStatus(task.status)"
									:show-info="false"
								/>
							</div>
						</div>
					</template>
					<a-button :loading="isUploading">
						{{ isUploading ? `正在上传 (${uploadQueue.length})` : '上传完成' }}
					</a-button>
				</a-popover>
			</div>

			<!-- 右侧筛选区 -->
			<div class="flex gap-2 items-center w-full md:w-auto">
				<a-input-search
					v-model:value="searchKeyword"
					placeholder="搜索文件名..."
					class="w-full md:w-56"
					@search="loadData(currentFolderId)"
					allow-clear
				/>
				<a-radio-group v-model:value="viewMode" button-style="solid">
					<a-radio-button value="list">
						<template #icon><UnorderedListOutlined /></template>
					</a-radio-button>
					<a-radio-button value="grid">
						<template #icon><AppstoreOutlined /></template>
					</a-radio-button>
				</a-radio-group>
			</div>
		</div>

		<!-- 面包屑导航 -->
		<div class="px-4 py-2 bg-gray-50 border-b border-gray-100 flex items-center text-sm overflow-x-auto whitespace-nowrap">
			<span class="text-gray-400 mr-2 flex-shrink-0">当前位置：</span>
			<a-breadcrumb separator="/">
				<a-breadcrumb-item>
					<a class="text-gray-600 hover:text-primary" @click="navigateTo(null)">
						<HomeOutlined /> 根目录
					</a>
				</a-breadcrumb-item>
				<a-breadcrumb-item v-for="(folder, index) in breadcrumbStack" :key="folder.id">
					<a class="text-gray-600 hover:text-primary" @click="navigateTo(folder.id, index)">
						{{ folder.name }}
					</a>
				</a-breadcrumb-item>
			</a-breadcrumb>
		</div>

		<!-- 主内容区 -->
		<div class="flex-1 overflow-hidden relative" v-loading="loading">

			<!-- 列表视图 -->
			<div v-if="viewMode === 'list'" class="h-full overflow-y-auto">
				<a-table
					:dataSource="fileList"
					:columns="columns"
					rowKey="id"
					:pagination="false"
					:sticky="true"
				>
					<template #bodyCell="{ column, record }">
						<template v-if="column.key === 'name'">
							<div class="flex items-center cursor-pointer group" @click="handleItemClick(record)">
								<component
									:is="getFileIcon(record)"
									class="text-2xl mr-3 flex-shrink-0"
									:class="record.isFolder ? 'text-yellow-400' : 'text-blue-400'"
								/>
								<span class="group-hover:text-primary transition-colors truncate">{{ record.name }}</span>
							</div>
						</template>
						<template v-else-if="column.key === 'size'">
							<span class="text-gray-400">{{ record.isFolder ? '-' : formatSize(record.fileSize) }}</span>
						</template>
						<template v-else-if="column.key === 'updateTime'">
							<span class="text-gray-500">{{ record.updateTime || record.createTime || '-' }}</span>
						</template>
						<template v-else-if="column.key === 'action'">
							<a-space>
								<a class="text-blue-500 hover:text-blue-700" @click.stop="openMoveModal(record)">移动</a>
								<a-popconfirm title="确定要删除此文件吗？" @confirm="handleDelete(record)">
									<a class="text-red-500 hover:text-red-700">删除</a>
								</a-popconfirm>
							</a-space>
						</template>
					</template>
				</a-table>
			</div>

			<!-- 网格视图 -->
			<div v-else class="h-full overflow-y-auto p-4">
				<div class="grid grid-cols-2 sm:grid-cols-4 md:grid-cols-6 lg:grid-cols-8 xl:grid-cols-10 gap-4">
					<div
						v-for="item in fileList"
						:key="item.id"
						class="group relative border border-gray-200 rounded-lg p-4 flex flex-col items-center cursor-pointer hover:shadow-md hover:border-primary hover:bg-blue-50 transition-all bg-white"
						@click="handleItemClick(item)"
					>
						<div class="text-5xl mb-3 transition-transform group-hover:scale-110">
							<component
								:is="getFileIcon(item)"
								:class="item.isFolder ? 'text-yellow-400' : 'text-blue-400'"
							/>
						</div>
						<div class="text-center w-full">
							<div class="truncate text-sm font-medium text-gray-700" :title="item.name">{{ item.name }}</div>
							<div class="text-xs text-gray-400 mt-1">{{ item.isFolder ? item.updateTime : formatSize(item.fileSize) }}</div>
						</div>

						<!-- 悬浮操作菜单 -->
						<div class="absolute top-2 right-2 opacity-0 group-hover:opacity-100 transition-opacity">
							<a-dropdown trigger="click" @click.stop>
								<a-button type="text" size="small" class="bg-white/80 hover:bg-white shadow-sm rounded-full !px-1">
									<MoreOutlined />
								</a-button>
								<template #overlay>
									<a-menu>
										<a-menu-item @click="openMoveModal(item)">移动到...</a-menu-item>
										<a-menu-item danger @click="handleDelete(item)">删除</a-menu-item>
									</a-menu>
								</template>
							</a-dropdown>
						</div>
					</div>
				</div>
				<a-empty v-if="fileList.length === 0" description="暂无文件" class="mt-20" />
			</div>
		</div>

		<!-- 隐藏的文件输入框 -->
		<input type="file" ref="fileInputRef" class="hidden" multiple @change="handleFileChange" />

		<!-- 新建文件夹弹窗 -->
		<a-modal
			v-model:open="createFolderModal.visible"
			title="新建文件夹"
			@ok="handleCreateFolderSubmit"
			:confirmLoading="createFolderModal.loading"
			destroyOnClose
		>
			<a-form
				ref="createFolderFormRef"
				:model="createFolderModal.form"
				:rules="createFolderRules"
				layout="vertical"
			>
				<a-form-item label="文件夹名称" name="name">
					<a-input v-model:value="createFolderModal.form.name" placeholder="请输入文件夹名称" allow-clear />
				</a-form-item>
				<a-form-item label="排序" name="sortCode">
					<a-input-number v-model:value="createFolderModal.form.sortCode" class="w-full" placeholder="请输入排序号" :min="0" :step="1" />
				</a-form-item>
			</a-form>
		</a-modal>

		<!-- 移动文件弹窗 -->
		<a-modal
			v-model:open="moveModal.visible"
			title="移动文件"
			@ok="handleMoveSubmit"
			:confirmLoading="moveModal.loading"
			destroyOnClose
		>
			<a-form layout="vertical">
				<a-form-item label="当前选中文件">
					<a-input disabled :value="moveModal.currentItem?.name" />
				</a-form-item>
				<a-form-item label="选择目标文件夹">
					<a-tree-select
						v-model:value="moveModal.targetId"
						style="width: 100%"
						:dropdown-style="{ maxHeight: '400px', overflow: 'auto' }"
						placeholder="请选择目标文件夹"
						allow-clear
						tree-default-expand-all
						:tree-data="moveModal.treeData"
						:load-data="onLoadFolderData"
						:fieldNames="{ children: 'children', label: 'name', value: 'id', isLeaf: 'isLeaf' }"
					>
						<template #title="{ name }">
							<FolderOutlined class="text-yellow-400 mr-1" /> {{ name }}
						</template>
					</a-tree-select>
				</a-form-item>
			</a-form>
		</a-modal>
	</div>
</template>

<script setup name="XdFileManager">
import {ref, computed, onMounted} from 'vue';
import {message, Modal} from 'ant-design-vue';
// 引入 Ant Design 图标
import {
	CloudUploadOutlined, FolderAddOutlined, HomeOutlined,
	UnorderedListOutlined, AppstoreOutlined, MoreOutlined,
	FolderOutlined, FolderOpenOutlined, FileOutlined,
	FileImageOutlined, FilePdfOutlined, FileWordOutlined,
	FileExcelOutlined, FilePptOutlined, FileTextOutlined,
	FileZipOutlined, FileMarkdownOutlined
} from '@ant-design/icons-vue';
// 引入 API
import fileApi from '@/api/file';


// --- 状态定义 ---
const loading = ref(false);
const fileList = ref([]);
const currentFolderId = ref(0);
const breadcrumbStack = ref([]); // 面包屑栈 {id, name}
const searchKeyword = ref('');
const viewMode = ref('list'); // 'list' | 'grid'
const fileInputRef = ref(null);

// 上传队列
const uploadQueue = ref([]); // { id, name, progress, status: 'uploading'|'done'|'error', file }
const isUploading = computed(() => uploadQueue.value.some(t => t.status === 'uploading'));

// 新建文件夹模态框
const createFolderFormRef = ref();
const createFolderModal = ref({
	visible: false,
	loading: false,
	form: {
		name: '',
		sortCode: 99
	}
});
const createFolderRules = {
	name: [{required: true, message: '请输入文件夹名称', trigger: 'blur'}]
};

// 移动模态框
const moveModal = ref({
	visible: false,
	loading: false,
	currentItem: null,
	targetId: null,
	treeData: []
});

// 表格列定义
const columns = [
	{title: '文件名', dataIndex: 'name', key: 'name', width: '50%'},
	{title: '大小', dataIndex: 'fileSize', key: 'size', width: '15%'},
	{title: '修改时间', dataIndex: 'updateTime', key: 'updateTime', width: '25%'},
	{title: '操作', key: 'action', width: '10%', align: 'center'}
];

// --- 初始化 ---
onMounted(() => {
	loadData();
});

// --- 数据加载 ---
const loadData = async (parentId = null) => {
	loading.value = true;
	try {
		// 调用 getList 接口
		const res = await fileApi.getList(parentId);
		// 这里假设后端返回的是数组，如果是在 data 字段中，请调整为 res.data
		let list = Array.isArray(res) ? res : (res.data || []);

		// 前端搜索过滤 (如果后端不支持搜索参数)
		if (searchKeyword.value) {
			list = list.filter(item => item.name.toLowerCase().includes(searchKeyword.value.toLowerCase()));
		}

		// 排序：文件夹在前
		fileList.value = list.sort((a, b) => {
			if (a.isFolder === b.isFolder) return 0;
			return a.isFolder ? -1 : 1;
		});
	} catch (error) {
		console.error(error);
		message.error('加载文件列表失败');
	} finally {
		loading.value = false;
	}
};

// --- 导航操作 ---
const navigateTo = (folderId, index = -1) => {
	searchKeyword.value = '';
	currentFolderId.value = folderId;

	if (index === -1) {
		// 回到根目录
		breadcrumbStack.value = [];
	} else {
		// 回到中间某一级
		breadcrumbStack.value = breadcrumbStack.value.slice(0, index + 1);
	}

	loadData(folderId);
};

const handleItemClick = (item) => {
	if (item.isFolder) {
		// 进入文件夹
		breadcrumbStack.value.push({id: item.id, name: item.name});
		currentFolderId.value = item.id;
		searchKeyword.value = ''; // 清空搜索以便查看文件夹内容
		loadData(item.id);
	} else {
		// 预览文件 (这里简单提示，实际可调用 preview 接口)
		message.info(`选中文件：${item.name}`);
	}
};

// --- 新建文件夹 ---
const handleCreateFolder = () => {
	createFolderModal.value.form = {
		name: '',
		sortCode: 99
	};
	createFolderModal.value.visible = true;
};

const handleCreateFolderSubmit = () => {
	createFolderFormRef.value.validate().then(() => {
		createFolderModal.value.loading = true;
		fileApi.createFolder({
			name: createFolderModal.value.form.name,
			sortCode: createFolderModal.value.form.sortCode,
			parentId: currentFolderId.value
		}).then(() => {
			message.success('创建成功');
			createFolderModal.value.visible = false;
			loadData(currentFolderId.value);
		}).catch(error => {
			message.error(error.message || '创建失败');
		}).finally(() => {
			createFolderModal.value.loading = false;
		});
	});
};

// --- 上传逻辑 (分片上传) ---
const triggerUpload = () => {
	fileInputRef.value.click();
};

const handleFileChange = async (e) => {
	const files = Array.from(e.target.files);
	if (!files.length) return;

	for (const file of files) {
		const task = {
			id: Date.now() + Math.random(),
			name: file.name,
			progress: 0,
			status: 'uploading'
		};
		uploadQueue.value.push(task);

		processUpload(file, task);
	}
	// 重置 input 防止同名文件不触发 change
	e.target.value = '';
};

const processUpload = async (file, task) => {
	try {
		const chunkSize = 2 * 1024 * 1024; // 2MB 分片
		const totalChunks = Math.ceil(file.size / chunkSize);

		// 生成简易 Hash (生产环境建议用 spark-md5 读取文件内容)
		const hashStr = `${file.name}-${file.size}-${file.lastModified}`;
		const hash = btoa(encodeURIComponent(hashStr));

		for (let i = 0; i < totalChunks; i++) {
			if (task.status === 'error') break;

			const start = i * chunkSize;
			const end = Math.min(file.size, start + chunkSize);
			const chunkBlob = file.slice(start, end);

			const formData = new FormData();
			formData.append('chunk', chunkBlob);
			formData.append('hash', hash);
			formData.append('index', i);
			formData.append('fileName', file.name); // 有些后端可能需要在 chunk 阶段校验文件名

			await fileApi.uploadChunk(formData, (progressEvent) => {
				// 单个分片进度可以忽略，主要看分片完成数
			});

			// 更新总体进度 (预留 10% 给合并阶段)
			task.progress = Math.floor(((i + 1) / totalChunks) * 90);
		}

		// 合并分片
		if (task.status !== 'error') {
			await fileApi.mergeChunks({
				hash: hash,
				fileName: file.name,
				parentId: currentFolderId.value
			});
			task.progress = 100;
			task.status = 'done';
			message.success(`${file.name} 上传成功`);
			loadData(currentFolderId.value); // 刷新列表
		}
	} catch (error) {
		console.error(error);
		task.status = 'error';
		message.error(`${file.name} 上传失败`);
	}
};

// --- 删除逻辑 ---
const handleDelete = async (record) => {
	try {
		await fileApi.deleteFile(record.id);
		message.success('删除成功');
		loadData(currentFolderId.value);
	} catch (error) {
		message.error('删除失败');
	}
};

// --- 移动逻辑 ---
const openMoveModal = async (record) => {
	moveModal.value.currentItem = record;
	moveModal.value.visible = true;
	moveModal.value.targetId = null;
	// 初始化根节点用于选择
	moveModal.value.treeData = [
		{id: 'root', name: '根目录', isLeaf: false, value: 'root', key: 'root'}
	];
};

const onLoadFolderData = (treeNode) => {
	return new Promise(async (resolve) => {
		if (treeNode.dataRef.children && treeNode.dataRef.children.length > 0) {
			resolve();
			return;
		}

		const parentId = treeNode.dataRef.id === 'root' ? null : treeNode.dataRef.id;
		try {
			const res = await fileApi.getList(parentId);
			const list = Array.isArray(res) ? res : (res.data || []);

			// 只筛选文件夹，并排除自己（如果是移动文件夹，不能移动到自己内部）
			const folders = list
				.filter(item => item.isFolder && item.id !== moveModal.value.currentItem?.id)
				.map(item => ({
					id: item.id,
					value: item.id,
					key: item.id,
					name: item.name,
					title: item.name,
					isLeaf: false // 假设所有文件夹都有可能包含子文件夹，实现无限懒加载
				}));

			treeNode.dataRef.children = folders;
			moveModal.value.treeData = [...moveModal.value.treeData]; // 触发响应式更新
			resolve();
		} catch (e) {
			resolve();
		}
	});
};

const handleMoveSubmit = async () => {
	if (!moveModal.value.targetId) {
		message.warning('请选择目标文件夹');
		return;
	}

	const targetId = moveModal.value.targetId === 'root' ? null : moveModal.value.targetId;
	// 检查是否移动到当前所在目录
	if (targetId === currentFolderId.value) {
		message.warning('文件已在当前目录下');
		return;
	}

	moveModal.value.loading = true;
	try {
		await fileApi.moveFile({
			fileId: moveModal.value.currentItem.id,
			targetId: targetId
		});
		message.success('移动成功');
		moveModal.value.visible = false;
		loadData(currentFolderId.value);
	} catch (error) {
		message.error('移动失败');
	} finally {
		moveModal.value.loading = false;
	}
};

// --- 工具函数 ---
const formatSize = (size) => {
	if (size === undefined || size === null) return '0 B';
	if (size < 1024) return size + ' B';
	else if (size < 1024 * 1024) return (size / 1024).toFixed(2) + ' KB';
	else if (size < 1024 * 1024 * 1024) return (size / 1024 / 1024).toFixed(2) + ' MB';
	else return (size / 1024 / 1024 / 1024).toFixed(2) + ' GB';
};

const getFileIcon = (file) => {
	if (file.isFolder) return file.id === currentFolderId.value ? FolderOpenOutlined : FolderOutlined;
	const name = file.name.toLowerCase();
	if (name.endsWith('.jpg') || name.endsWith('.png') || name.endsWith('.gif')) return FileImageOutlined;
	if (name.endsWith('.pdf')) return FilePdfOutlined;
	if (name.endsWith('.doc') || name.endsWith('.docx')) return FileWordOutlined;
	if (name.endsWith('.xls') || name.endsWith('.xlsx')) return FileExcelOutlined;
	if (name.endsWith('.ppt') || name.endsWith('.pptx')) return FilePptOutlined;
	if (name.endsWith('.txt')) return FileTextOutlined;
	if (name.endsWith('.zip') || name.endsWith('.rar')) return FileZipOutlined;
	if (name.endsWith('.md')) return FileMarkdownOutlined;
	return FileOutlined;
};

const getUploadStatus = (status) => {
	if (status === 'error') return 'exception';
	if (status === 'done') return 'success';
	return 'active';
};
</script>

<style lang="less" scoped>
.xd-file-manager {
	/* 自定义滚动条样式 */

	.custom-scrollbar {
		&::-webkit-scrollbar {
			width: 6px;
		}

		&::-webkit-scrollbar-track {
			background: #f1f1f1;
		}

		&::-webkit-scrollbar-thumb {
			background: #ccc;
			border-radius: 3px;
		}

		&::-webkit-scrollbar-thumb:hover {
			background: #aaa;
		}
	}
}
</style>
