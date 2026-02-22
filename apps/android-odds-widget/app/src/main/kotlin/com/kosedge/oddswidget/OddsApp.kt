package com.kosedge.oddswidget

import android.app.Application
import android.util.Log
import androidx.work.Configuration
import androidx.work.ExistingPeriodicWorkPolicy
import androidx.work.PeriodicWorkRequestBuilder
import androidx.work.WorkManager
import java.util.concurrent.TimeUnit

class OddsApp : Application(), Configuration.Provider {

    override val workManagerConfiguration: Configuration
        get() = Configuration.Builder()
            .setMinimumLoggingLevel(Log.DEBUG)
            .build()

    override fun onCreate() {
        super.onCreate()
        // By implementing Configuration.Provider, we provide on-demand initialization
        // for WorkManager. The system initializes it for us, so we should not call
        // WorkManager.initialize() manually. We just need to schedule the work.
        try {
            scheduleHourlyWork()
        } catch (e: Exception) {
            Log.e(TAG, "WorkManager scheduling failed", e)
        }
    }

    private fun scheduleHourlyWork() {
        try {
            val request = PeriodicWorkRequestBuilder<OddsWorker>(1, TimeUnit.HOURS)
                .build()
            // getInstance() will automatically use our provider for initialization.
            WorkManager.getInstance(this).enqueueUniquePeriodicWork(
                OddsWorker.WORK_NAME,
                ExistingPeriodicWorkPolicy.KEEP,
                request
            )
        } catch (e: Exception) {
            Log.e(TAG, "Schedule work failed", e)
        }
    }

    companion object {
        private const val TAG = "OddsApp"
    }
}
