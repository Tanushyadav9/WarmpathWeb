import 'package:flutter/material.dart';
import '../../core/theme/tokens.dart';
import '../../core/widgets/w_button.dart';
import '../../core/widgets/w_card.dart';

class AvailabilityPage extends StatefulWidget {
  const AvailabilityPage({super.key});

  @override
  State<AvailabilityPage> createState() => _AvailabilityPageState();
}

class _AvailabilityPageState extends State<AvailabilityPage> {
  String _status = 'available_today'; // 'active_now', 'available_today', 'inactive'
  final TextEditingController _windowController = TextEditingController(text: '8 to 10 pm');
  int _weeklyCapacityCap = 5;
  int _weeklySessionsUsed = 2;
  int _monthlyFreeSessionCap = 10;
  int _monthlyFreeSessionsUsed = 3;
  double _responseRate = 95.0;
  String _avgReplyTime = '2h';
  bool _isSaving = false;

  bool get _isCapacityReached =>
      (_weeklySessionsUsed >= _weeklyCapacityCap) ||
      (_monthlyFreeSessionsUsed >= _monthlyFreeSessionCap);

  Color _getStatusColor(String status) {
    switch (status) {
      case 'active_now':
        return AppColors.successGreen;
      case 'available_today':
        return AppColors.amber;
      case 'inactive':
      default:
        return AppColors.slate;
    }
  }

  String _getStatusLabel(String status) {
    switch (status) {
      case 'active_now':
        return 'Active now';
      case 'available_today':
        return 'Available today';
      case 'inactive':
      default:
        return 'Inactive';
    }
  }

  @override
  void dispose() {
    _windowController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('My Availability & Limits'),
        backgroundColor: AppColors.white,
      ),
      body: ListView(
        padding: const EdgeInsets.all(16.0),
        children: [
          // Capacity Reached Banner
          if (_isCapacityReached) ...[
            Container(
              margin: const EdgeInsets.only(bottom: 16.0),
              padding: const EdgeInsets.all(14.0),
              decoration: BoxDecoration(
                color: const Color(0xFFFEF2F2),
                borderRadius: AppRadii.card,
                border: Border.all(color: const Color(0xFFFCA5A5), width: 1.5),
              ),
              child: const Row(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Icon(Icons.warning_amber_rounded, color: Color(0xFFDC2626), size: 24),
                  SizedBox(width: 12),
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(
                          'Capacity Reached',
                          style: TextStyle(
                            fontSize: 15,
                            fontWeight: FontWeight.bold,
                            color: Color(0xFF991B1B),
                          ),
                        ),
                        SizedBox(height: 4),
                        Text(
                          'You have reached your session limit for this period. You are temporarily paused from student matching until capacity resets.',
                          style: TextStyle(fontSize: 13, color: Color(0xFF7F1D1D)),
                        ),
                      ],
                    ),
                  ),
                ],
              ),
            ),
          ],

          // Real-time Metrics Card
          WCard(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                const Text(
                  'Historical Performance Metrics',
                  style: TextStyle(fontSize: 16, fontWeight: FontWeight.bold, color: AppColors.textDark),
                ),
                const SizedBox(height: 12),
                Row(
                  children: [
                    Expanded(
                      child: Container(
                        padding: const EdgeInsets.all(12),
                        decoration: BoxDecoration(
                          color: AppColors.surface,
                          borderRadius: AppRadii.badge,
                        ),
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            const Text('Response Rate', style: TextStyle(fontSize: 12, color: AppColors.slate)),
                            const SizedBox(height: 4),
                            Text(
                              '${_responseRate.toStringAsFixed(0)}%',
                              style: const TextStyle(fontSize: 20, fontWeight: FontWeight.bold, color: AppColors.teal),
                            ),
                          ],
                        ),
                      ),
                    ),
                    const SizedBox(width: 12),
                    Expanded(
                      child: Container(
                        padding: const EdgeInsets.all(12),
                        decoration: BoxDecoration(
                          color: AppColors.surface,
                          borderRadius: AppRadii.badge,
                        ),
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            const Text('Average Reply Time', style: TextStyle(fontSize: 12, color: AppColors.slate)),
                            const SizedBox(height: 4),
                            Text(
                              _avgReplyTime,
                              style: const TextStyle(fontSize: 20, fontWeight: FontWeight.bold, color: AppColors.deepIndigo),
                            ),
                          ],
                        ),
                      ),
                    ),
                  ],
                ),
              ],
            ),
          ),
          const SizedBox(height: 16),

          // Giver Status Selector
          WCard(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Row(
                  mainAxisAlignment: MainAxisAlignment.spaceBetween,
                  children: [
                    const Text(
                      'Current Giver Status',
                      style: TextStyle(fontSize: 16, fontWeight: FontWeight.bold, color: AppColors.textDark),
                    ),
                    // Colored dot indicator
                    Row(
                      children: [
                        Container(
                          width: 10,
                          height: 10,
                          decoration: BoxDecoration(
                            color: _getStatusColor(_status),
                            shape: BoxShape.circle,
                          ),
                        ),
                        const SizedBox(width: 6),
                        Text(
                          _getStatusLabel(_status),
                          style: TextStyle(
                            fontSize: 13,
                            fontWeight: FontWeight.w600,
                            color: _getStatusColor(_status),
                          ),
                        ),
                      ],
                    ),
                  ],
                ),
                const SizedBox(height: 14),

                // Status options
                RadioListTile<String>(
                  value: 'active_now',
                  groupValue: _status,
                  title: const Text('Active now', style: TextStyle(fontWeight: FontWeight.w600)),
                  subtitle: const Text('Open 30-minute instant connect window for urgent questions'),
                  secondary: const Icon(Icons.bolt, color: AppColors.successGreen),
                  onChanged: (val) {
                    if (val != null) setState(() => _status = val);
                  },
                ),
                RadioListTile<String>(
                  value: 'available_today',
                  groupValue: _status,
                  title: const Text('Available today', style: TextStyle(fontWeight: FontWeight.w600)),
                  subtitle: const Text('Accept requests during your daily availability window'),
                  secondary: const Icon(Icons.calendar_today, color: AppColors.amber),
                  onChanged: (val) {
                    if (val != null) setState(() => _status = val);
                  },
                ),
                if (_status == 'available_today') ...[
                  Padding(
                    padding: const EdgeInsets.only(left: 16.0, right: 16.0, bottom: 8.0),
                    child: TextField(
                      controller: _windowController,
                      decoration: const InputDecoration(
                        labelText: 'Time window (e.g. 8 to 10 pm)',
                        border: OutlineInputBorder(),
                        isDense: true,
                      ),
                    ),
                  ),
                ],
                RadioListTile<String>(
                  value: 'inactive',
                  groupValue: _status,
                  title: const Text('Inactive', style: TextStyle(fontWeight: FontWeight.w600)),
                  subtitle: const Text('Temporarily offline. Stale after 7 days auto-switches here.'),
                  secondary: const Icon(Icons.bedtime_outlined, color: AppColors.slate),
                  onChanged: (val) {
                    if (val != null) setState(() => _status = val);
                  },
                ),
              ],
            ),
          ),
          const SizedBox(height: 16),

          // Capacity Limits Card
          WCard(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                const Text(
                  'Capacity Caps & Workload',
                  style: TextStyle(fontSize: 16, fontWeight: FontWeight.bold, color: AppColors.textDark),
                ),
                const SizedBox(height: 14),

                // Weekly capacity cap
                Row(
                  mainAxisAlignment: MainAxisAlignment.spaceBetween,
                  children: [
                    const Text('Weekly Capacity Cap:', style: TextStyle(fontSize: 14)),
                    Text(
                      '$_weeklySessionsUsed / $_weeklyCapacityCap sessions',
                      style: TextStyle(
                        fontSize: 14,
                        fontWeight: FontWeight.bold,
                        color: _weeklySessionsUsed >= _weeklyCapacityCap ? Colors.red : AppColors.deepIndigo,
                      ),
                    ),
                  ],
                ),
                Slider(
                  value: _weeklyCapacityCap.toDouble(),
                  min: 1,
                  max: 20,
                  divisions: 19,
                  label: '$_weeklyCapacityCap sessions',
                  onChanged: (val) => setState(() => _weeklyCapacityCap = val.toInt()),
                ),

                const SizedBox(height: 10),

                // Monthly free-session cap
                Row(
                  mainAxisAlignment: MainAxisAlignment.spaceBetween,
                  children: [
                    const Text('Monthly Free-Session Cap:', style: TextStyle(fontSize: 14)),
                    Text(
                      '$_monthlyFreeSessionsUsed / $_monthlyFreeSessionCap free sessions',
                      style: TextStyle(
                        fontSize: 14,
                        fontWeight: FontWeight.bold,
                        color: _monthlyFreeSessionsUsed >= _monthlyFreeSessionCap ? Colors.red : AppColors.deepIndigo,
                      ),
                    ),
                  ],
                ),
                Slider(
                  value: _monthlyFreeSessionCap.toDouble(),
                  min: 1,
                  max: 30,
                  divisions: 29,
                  label: '$_monthlyFreeSessionCap sessions',
                  onChanged: (val) => setState(() => _monthlyFreeSessionCap = val.toInt()),
                ),
              ],
            ),
          ),
          const SizedBox(height: 24),

          // Save button
          WButton(
            text: _isSaving ? 'Saving...' : 'Save Availability & Limits',
            onPressed: () {
              ScaffoldMessenger.of(context).showSnackBar(
                const SnackBar(content: Text('Availability and limits saved successfully!')),
              );
            },
          ),
        ],
      ),
    );
  }
}
