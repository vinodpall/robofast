<template>
  <!-- No changes to template section -->
</template>

<script>
import { ref } from 'vue'
import { ElMessage } from 'element-plus'

export default {
  setup() {
    const videoForm = ref({})
    const dialogVisible = ref(false)
    const loading = ref(false)
    const currentPage = ref(1)
    const pageSize = ref(10)
    const filterForm = ref({})
    const videoList = ref([])
    const total = ref(0)

    // 创建视频
    const handleCreate = async () => {
      try {
        const formData = new FormData()
        formData.append('name', videoForm.value.name)
        formData.append('type', videoForm.value.type)
        formData.append('description', videoForm.value.description || '')
        formData.append('is_carousel', 'false')
        
        if (videoForm.value.type === 'LOCAL') {
          // 如果是本地视频，需要上传文件
          const fileInput = document.querySelector('.video-uploader input[type="file"]')
          if (fileInput && fileInput.files.length > 0) {
            formData.append('file', fileInput.files[0])
          }
        } else {
          // 如果是 RTSP 或 WEB 类型，直接使用 URL
          formData.append('url', videoForm.value.url)
        }

        // 打印请求数据
        console.log('发送的表单数据:')
        for (let pair of formData.entries()) {
          console.log(pair[0] + ': ' + pair[1])
        }

        const response = await api.post('/videos', formData, {
          headers: {
            'Content-Type': 'multipart/form-data'
          }
        })
        ElMessage.success('创建成功')
        dialogVisible.value = false
        fetchVideoList()
      } catch (error) {
        console.error('创建失败:', error)
        if (error.response) {
          console.error('错误状态码:', error.response.status)
          console.error('错误数据:', error.response.data)
          console.error('错误详情:', error.response.data.detail || error.response.data)
        }
        ElMessage.error(error.response?.data?.detail || '创建失败')
      }
    }

    const fetchVideoList = async () => {
      loading.value = true
      try {
        const params = {
          page: currentPage.value,
          page_size: pageSize.value,
          name: filterForm.value.name || undefined,
          video_type: filterForm.value.type || undefined
        }
        
        console.log('筛选条件:', filterForm.value)
        console.log('请求参数:', params)
        
        const response = await api.get('/videos', { params })
        console.log('响应数据:', response)
        
        videoList.value = response.items.map(item => ({
          ...item,
          id: item.id,
          name: item.name,
          description: item.description || '',
          url: item.url || '',
          type: item.type,  // 直接使用后端返回的类型
          is_carousel: item.is_carousel || false,
          create_time: item.create_time || item.createTime,
          carousel_add_time: item.carousel_add_time || null
        }))
        total.value = response.total
      } catch (error) {
        console.error('获取视频列表失败:', error)
        console.error('错误详情:', error.response)
        ElMessage.error('获取视频列表失败')
      } finally {
        loading.value = false
      }
    }

    return {
      videoForm,
      dialogVisible,
      handleCreate,
      loading,
      currentPage,
      pageSize,
      filterForm,
      videoList,
      total
    }
  }
}
</script>

<style>
  /* No changes to style section */
</style> 