const startVideo = (index) => {
  const frame = videoFrames.value[index]
  console.log(`开始播放视频 ${index}:`, frame)
  
  if (frame.isRtsp) {
    // RTSP视频流处理
    // ... 现有的RTSP处理代码 ...
  } else {
    // 本地视频处理
    const video = videoRefs.value[index]
    if (video) {
      console.log('开始播放本地视频:', frame.url)
      // 如果是本地视频，使用完整的URL
      const baseUrl = window.location.origin
      video.src = frame.url.startsWith('http') ? frame.url : `${baseUrl}${frame.url}`
      video.play().catch(error => {
        console.error('视频播放失败:', error)
      })
    } else {
      console.error('视频元素不存在')
    }
  }
} 