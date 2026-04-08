package com.kosedge.oddswidget

import android.content.Context
import androidx.work.CoroutineWorker
import androidx.work.WorkerParameters
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import java.net.URL
import java.util.Calendar

class OddsWorker(context: Context, params: WorkerParameters) : CoroutineWorker(context, params) {

    override suspend fun doWork(): Result = withContext(Dispatchers.IO) {
        val cal = Calendar.getInstance()
        val hour = cal.get(Calendar.HOUR_OF_DAY)
        if (hour < 6 || hour >= 22) {
            return@withContext Result.success()
        }
        try {
            val json = URL(API_URL).readText()
            OddsPrefs.saveOddsJson(applicationContext, json)
            OddsWidget.updateAllWidgets(applicationContext)
            Result.success()
        } catch (e: Exception) {
            Result.retry()
        }
    }

    companion object {
        const val WORK_NAME = "odds_refresh"
        private const val API_URL = "https://www.kosedge.com/api/edge-board/ncaam/today"

        fun runOnce(context: Context) {
            val request = androidx.work.OneTimeWorkRequestBuilder<OddsWorker>().build()
            androidx.work.WorkManager.getInstance(context).enqueue(request)
        }
    }
}
