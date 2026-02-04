import { baseRequest } from '@/utils/request'

const request = (url, ...arg) => baseRequest(`/filemanger/` + url, ...arg)

/**
 * 项目表Api接口管理器
 *
 * @author Richai
 * @date  2025/12/24 16:30
 **/
export default {

	/**
	 * 获取文件列表
	 * @param {string|null} parentId 父文件夹ID，根目录传 null
	 */
	getList(data) {
		return request('list', data, 'get')
	},
	// getList(parentId) {
	// 	return request({
	// 		url: 'list',
	// 		method: 'get',
	// 		params: { parentId }
	// 	})
	// },

	// 获取项目表分页
	createFolder(data) {
		return request('folder', data)
	},
	/**
	 * 上传分片
	 * @param {FormData} formData 包含 chunk, hash, index, fileName
	 * @param {function} onUploadProgress 上传进度回调
	 */
	uploadChunk(formData, onUploadProgress) {
		return request({
			url: 'upload/chunk',
			method: 'post',
			data: formData,
			// 允许上传大文件，根据需要调整超时时间
			timeout: 0,
			onUploadProgress
		})
	},

	/**
	 * 合并分片
	 * @param {object} data { hash: 'xxx', fileName: 'xxx', parentId: 'xxx' }
	 */
	mergeChunks(data) {
		return request({
			url: 'upload/merge',
			method: 'post',
			data
		})
	},

	/**
	 * 删除文件/文件夹
	 * @param {string} id 文件ID
	 */
	deleteFile(id) {
		return request({
			url: 'delete',
			method: 'post',
			data: { id }
		})
	},

	/**
	 * 移动文件
	 * @param {object} data { fileId: 'xxx', targetId: 'xxx' }
	 */
	moveFile(data) {
		return request({
			url: 'file/move',
			method: 'post',
			data
		})
	}

}
