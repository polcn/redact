// Test script to verify the "already signed in user" fix
// Run with: node test-auth-fix.js

const puppeteer = require('puppeteer');

const TEST_CONFIG = {
  url: 'http://localhost:3000',
  user1: {
    email: 'test1@gmail.com',
    password: 'TestPassword123!'
  },
  user2: {
    email: 'test2@gmail.com', 
    password: 'TestPassword456!'
  }
};

async function testAuthFix() {
  const browser = await puppeteer.launch({
    headless: false,
    slowMo: 50
  });

  try {
    const page = await browser.newPage();
    
    console.log('🧪 Test 1: Sign in with first user');
    await page.goto(`${TEST_CONFIG.url}/login`);
    await page.waitForSelector('#email');
    
    // Sign in with first user
    await page.type('#email', TEST_CONFIG.user1.email);
    await page.type('#password', TEST_CONFIG.user1.password);
    await page.click('button[type="submit"]');
    
    // Wait for redirect to home
    await page.waitForNavigation();
    console.log('✅ First user signed in successfully');
    
    console.log('🧪 Test 2: Navigate back to login page');
    await page.goto(`${TEST_CONFIG.url}/login`);
    
    // Should be redirected back to home
    await page.waitForTimeout(1000);
    const currentUrl = page.url();
    if (!currentUrl.includes('/login')) {
      console.log('✅ Already signed-in user redirected away from login');
    } else {
      console.log('❌ User was not redirected from login page');
    }
    
    console.log('🧪 Test 3: Force sign out and sign in with different user');
    // Sign out current user
    await page.evaluate(() => {
      localStorage.clear();
      sessionStorage.clear();
    });
    
    await page.goto(`${TEST_CONFIG.url}/login`);
    await page.waitForSelector('#email');
    
    // Sign in with second user
    await page.type('#email', TEST_CONFIG.user2.email);
    await page.type('#password', TEST_CONFIG.user2.password);
    await page.click('button[type="submit"]');
    
    // Check for error or successful login
    await page.waitForTimeout(2000);
    
    const errorElement = await page.$('.text-red-800');
    if (errorElement) {
      const errorText = await page.evaluate(el => el.textContent, errorElement);
      console.log('❌ Error occurred:', errorText);
    } else {
      console.log('✅ Second user signed in successfully (auto-signout worked)');
    }
    
    console.log('🧪 Test 4: Check console for sign-out message');
    const consoleLogs = [];
    page.on('console', msg => consoleLogs.push(msg.text()));
    
    // Try signing in again
    await page.goto(`${TEST_CONFIG.url}/login`);
    await page.waitForSelector('#email');
    await page.type('#email', TEST_CONFIG.user1.email);
    await page.type('#password', TEST_CONFIG.user1.password);
    await page.click('button[type="submit"]');
    
    await page.waitForTimeout(2000);
    
    const signOutLog = consoleLogs.find(log => 
      log.includes('Signing out existing user before new sign in')
    );
    
    if (signOutLog) {
      console.log('✅ Auto-signout message found in console');
    } else {
      console.log('⚠️  Auto-signout message not found in console');
    }
    
  } catch (error) {
    console.error('❌ Test failed:', error.message);
  } finally {
    await browser.close();
  }
}

// Run the test
testAuthFix().then(() => {
  console.log('🏁 Test completed');
}).catch(error => {
  console.error('💥 Test script error:', error);
});